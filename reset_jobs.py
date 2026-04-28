import json
import os

EXPORTS_BASE_PATH = r'D:\Zenith\exports'

for channel in os.listdir(EXPORTS_BASE_PATH):
    channel_path = os.path.join(EXPORTS_BASE_PATH, channel)
    if not os.path.isdir(channel_path):
        continue
    for job_folder in os.listdir(channel_path):
        job_file = os.path.join(channel_path, job_folder, 'job.json')
        if os.path.exists(job_file):
            with open(job_file, 'r', encoding='utf-8') as f:
                job = json.load(f)
            job['publish_status'] = 'pending'
            with open(job_file, 'w', encoding='utf-8') as f:
                json.dump(job, f, indent=4)
            print(job.get('job_id'), '-> pending')

print('Done!')