import pickle
from pathlib import Path

data_dir = Path("C:/Users/Trach_McGee/Desktop/Data")

if __name__=="__main__":
    subject_name = input("Enter Subject Name:")
    with open(Path(data_dir, subject_name, "random_dot_motion", "rt_dynamic_training", "rolling_performance.pkl"), "rb") as reader:
        rolling_perf = pickle.load(reader)  
    
    print(f"Current coherence level: {rolling_perf['current_coherence_level']}")
    print(f"Accuracy: {rolling_perf['accuracy']}")

    change_level = input("Change level? (y/n):")
    if change_level == "y":
        new_level = input("Enter new level:")
        rolling_perf["current_coherence_level"] = int(new_level)
        print(f"Current coherence level: {rolling_perf['current_coherence_level']}")
        print(f"Accuracy: {rolling_perf['accuracy']}")

        with open(Path(data_dir, subject_name, "random_dot_motion", "rt_dynamic_training", "rolling_performance.pkl"), "wb") as writer:
            pickle.dump(rolling_perf, writer)
    else:
        print("No change made")
        