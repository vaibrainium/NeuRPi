import h5py


# Function to create the HDF5 file structure
def create_hdf5_file():
    # Create the root HDF5 file
    with h5py.File("neuro_experiment.h5", "w") as file:
        # Create the 'info' group for subjects' biographical information
        info_group = file.create_group("info")

        # Create the 'history' group for historical records
        history_group = file.create_group("history")

        # Create the main 'data' group
        data_group = file.create_group("data")

        # Create the 'protocol' group
        protocol_group = data_group.create_group("protocol")

        # Create the 'experiment' group
        experiment_group = protocol_group.create_group("experiment")

        # Create the 'summary' group for task phase summary data
        summary_group = experiment_group.create_group("summary")

        # Create datasets for weight, performance, and parameters
        summary_group.create_dataset("weight", data=[60, 65, 70, 75])
        summary_group.create_dataset("performance", data=[0.8, 0.85, 0.9, 0.95])
        summary_group.create_dataset("parameters", data=["param1", "param2", "param3"])

        # Create directories for different sessions
        for session_num in range(1, 6):
            session_name = f"session_# {session_num}"
            session_group = experiment_group.create_group(session_name)

            # Create datasets for trial_data and continuous_data in each session
            session_group.create_dataset("trial_data", data=[1, 2, 3, 4, 5])
            session_group.create_dataset("continuous_data", data=[10, 20, 30, 40, 50])


if __name__ == "__main__":
    create_hdf5_file()
