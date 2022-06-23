import hydra

@hydra.main(version_base=None, config_path='conf', config_name='config_rdk')
def configutation_access(parameters):
    print(parameters)
    from tasks.task import Task

if __name__ == '__main__':
    configutation_access()
