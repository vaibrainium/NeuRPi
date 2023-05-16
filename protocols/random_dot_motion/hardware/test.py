from protocols.random_dot_motion.hardware.hardware_manager import HardwareManager

if __name__ == "__main__":
    import sys

    a = HardwareManager()

    while True:
        print("Press Enter to continue or enter reset command")
        cmd = input()
        count = 0
        if cmd:
            print("RESETTING")
            a.reset_lick_i2c()
        else:
            print("Start licking")
            while True:
                lick = a.read_licks()
                if lick != None:
                    count += 1
                    print(f"Lick: {lick}; Count: {count}")
                if count == 10:
                    break
