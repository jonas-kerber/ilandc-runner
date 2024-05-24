import os

if __name__ == "__main__":
    # get all the worker*.sh files in instruction_queues
    worker_files = []
    for file in os.listdir("instruction_queues"):
        if file.startswith("worker") and file.endswith(".sh"):
            worker_files.append(file)

    # start the workers in their own screen session
    for worker_file in worker_files:
        worker_name = worker_file.split(".")[0]
        session_name = f"ilandc-runner-{worker_name}"
        bash_command = f"bash instruction_queues/{worker_file}"
        screen_command = f'screen -dmS {session_name} bash -c "{bash_command}; screen -X -S {session_name} quit"'
        os.system(screen_command)
        print(f"Started worker: {worker_file}")
        print(screen_command)
        print()
