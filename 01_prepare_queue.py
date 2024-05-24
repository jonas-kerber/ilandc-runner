import os
import pandas as pd
import toml

# SETTINGS
FAIL_IF_ILAND_PROJECT_FOLDER_DOES_NOT_EXIST = False  # print warning otherwise
OUTPUT_FILE = "instruction_queues/all-commands.sh"


def get_input_projects(settings):
    input_projects = []
    # read the input file line by line
    input_files = settings["input"]["iland_project_list"]
    for input_file in input_files:
        # check if path exist and add them to the list
        path = input_file.strip()
        if os.path.exists(path):
            input_projects.append(path)
        else:
            if FAIL_IF_ILAND_PROJECT_FOLDER_DOES_NOT_EXIST:
                raise Exception(f"Path does not exist: {path}")
            else:
                print(f"Warning: Path does not exist: {path} -> ignoring")
    return input_projects


def get_input_table_files(input_projects):
    table_files = []
    for project in input_projects:
        for root, dirs, files in os.walk(project):
            for file in files:
                if file.endswith(".csv") or file.endswith(".xlsx"):
                    table_files.append(os.path.join(root, file))
    return table_files


def read_tables_from_files(input_table_files):
    df_dict = {}  # key: table name, value: dataframe
    for file in input_table_files:
        print(f"Reading file: {file}")
        # case 1: excel
        if file.endswith(".xlsx"):
            df = pd.read_excel(file, sheet_name=None)
            # Get the list of table names
            table_names = list(df.keys())
            # Load all tables into dataframes
            dataframes = [df[table_name] for table_name in table_names]
            df_dict[file] = dataframes
        # case 2: csv
        elif file.endswith(".csv"):
            df = pd.read_csv(file)
            df_dict[file] = df
    return df_dict


def check_already_completed_simulations(dataframe_dict):
    n_skipped = 0
    n_total = 0
    for project_folder, df_list in dataframe_dict.items():
        for df in df_list:
            df["skipped"] = False
            # iterate line by line and check if output file was already produced
            for i_row, row in df.iterrows():
                output_file = df["output_sqlite"]
                output_path = f"{project_folder}/output/{output_file}"
                if os.path.exists(output_path):
                    print(f"WARNING: skipping run_id {df["run_id"]} from project {project_folder} because {output_path} already exists")
                    print("      if you want to redo the simulation, delete or move the sqlite to a different folder")
                    n_skipped += 1
                    df["skipped"].iloc[i_row] = True
                n_total += 1
    print("Checked all simulations if there is already output:")
    print(f"  --> Skipped {n_skipped} out of {n_total} simulations.")


def convert_tables_into_ilandc_calls(dataframe_dict, ilandc_settings):
    # all the required columns for a run
    required_columns = ["run_id", "project_file", "sim_years", "output_sqlite"]
    # the optional arguments should match whatever is configurable in the iland project files
    # e.g. output.stand.enabled (ref: https://iland-model.org/iLand+console)
    optional_args_suffices = ["output", "system", "model", "modules"]

    lines = []
    for table_name, dataframes in dataframe_dict.items():
        for df in dataframes:
            lines.append(f"#{table_name}")
            # check if all required columns are present
            if not all(col in df.columns for col in required_columns):
                raise Exception(
                    f"Missing required columns in table: {df.columns}. Required columns are: {required_columns}"
                )
            # iterate over rows and create ilandc calls
            for _, row in df.iterrows():
                # skip all the rows that are marked as skipped
                run_id = row["run_id"]
                project_file = row["project_file"]
                sim_years = row["sim_years"]
                output_sqlite = row["output_sqlite"]
                ilandc_exe = ilandc_settings["general"]["path_to_ilandc_executable"]
                n_threads = ilandc_settings["threading"]["n_threads_per_worker"]
                # ilandc project.xml 100
                ilandc_command = f"ilandc {project_file} {sim_years} system.database.out={output_sqlite}"
                # add optional arguments
                for col in df.columns:
                    if col in required_columns or col == "skipped":
                        pass  # skip required columns
                    else:
                        # check if column name has correct format
                        format_incorrect = False
                        if "." not in col:
                            format_incorrect = True
                        else:
                            suffix = col.split(".")[0]
                            if suffix not in optional_args_suffices:
                                format_incorrect = True
                        #
                        if format_incorrect:
                            raise Exception(
                                f"Column name format incorrect: {col}. Correct format example: output.stand.enabled"
                            )
                        else:
                            ilandc_command += f" {col}={row[col]}"
                # add to the list
                if not row["skipped"]:
                    lines.append(ilandc_command)
                else:
                    # add the skipped command to the file status/skipped-commands.sh
                    with open("status/skipped-commands.sh", "a") as file:
                        file.write(ilandc_command + "\n")
        # write list of commands to file
        with open(OUTPUT_FILE, "w") as file:
            for command in lines:
                file.write(command + "\n")


if __name__ == "__main__":
    settings = toml.load("settings.toml")
    # clear all files inside the status folder
    for file in os.listdir("status"):
        os.remove(f"status/{file}")
    # get a list of all the given projects
    input_projects = get_input_projects(settings)
    # get all the tables in the projects
    input_table_files = get_input_table_files(input_projects)
    # read them as dataframes
    dataframes = read_tables_from_files(input_table_files)
    # check all the simulations that where already done
    check_already_completed_simulations(dataframes)
    # create the iland calls out of them
    convert_tables_into_ilandc_calls(dataframes, settings)

    # print info for next steps
    print("All instructions written to the file: instruction/queues/all-commands.sh")
    print("Continue running 'python 02_prepare_workers.py' or refer to README.")