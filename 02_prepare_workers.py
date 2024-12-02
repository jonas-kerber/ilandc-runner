import toml
import os

PRIORITY_PREFIX = "### Priority "


if __name__ == "__main__":
    # Read the TOML file
    with open("settings.toml", "r") as file:
        settings = toml.load(file)

    n_workers = settings["threading"]["n_workers"]
    n_threads_per_worker = settings["threading"]["n_threads_per_worker"]
    iland_suffix = f"system.settings.threadCount={n_threads_per_worker}"

    start_folder = os.path.dirname(os.path.abspath(__file__))

    # delete all file worker*.sh files in instruction_queues
    for file in os.listdir("instruction_queues"):
        if file.startswith("worker") and file.endswith(".sh"):
            os.remove(f"instruction_queues/{file}")

    # # create the empty worker files
    # for i in range(n_workers):
    #     # create them empty
    #     with open(f"instruction_queues/worker-{i}.sh", "w") as worker_file:
    #         worker_file.write("")

    # read "instruction_queues/all-commands.sh" line by line
    command_i = 0
    project_folder = None
    with open("instruction_queues/all-commands.sh", "r") as file:
        lines = file.readlines()
        for line in lines:
            # get the project path
            if line.startswith("#"):
                continue  # ignore
            # get the command
            else:
                command = line.strip()
                assigned_worker = command_i % n_workers
                command = f"{command} {iland_suffix}"
                # write command
                worker_filename = f"instruction_queues/worker-{assigned_worker}.sh"
                with open(worker_filename, "a") as worker_file:
                    worker_file.write(command + "\n")
                command_i += 1

    print(f"finished writing {command_i} commands to {n_workers} worker files.")
    print("Result scripts can be found in instruction_queues/worker-*.sh")
    print("You can start the workers with 03_start_workers.py")
