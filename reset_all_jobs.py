import json
from pathlib import Path

jobs_file = Path(r"D:\Zenith\data\jobs.json")
data = json.loads(jobs_file.read_text(encoding="utf-8"))

jobs_dict = data.get("jobs", {})

# Nur die zwei Rocket League Jobs löschen
to_delete = ["job_113e610b46f4", "job_5c4aa2c6ee9a"]
for job_id in to_delete:
    if job_id in jobs_dict:
        del jobs_dict[job_id]
        print(f'{job_id} -> gelöscht')

jobs_file.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
print("Done! Pipeline wird sie neu erstellen.")