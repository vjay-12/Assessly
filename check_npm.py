import os, subprocess, sys

for app in ['candidate-portal', 'assessment-engine', 'employer-dashboard']:
    path = f'apps/{app}/node_modules'
    exists = os.path.exists(path)
    print(f'{app}: node_modules exists = {exists}')
    if exists:
        count = len(os.listdir(path))
        print(f'  {count} packages installed')
