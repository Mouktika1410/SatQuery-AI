import os
import subprocess

def restore_commit():
    target_commit = "d2b7600"
    log_file = r"c:\SatQuery\scripts\restore_output.txt"
    files_to_restore = [
        "Frontend/src/components/MapViewer.jsx",
        "Backend/app/services/polygon_generation.py",
        "Backend/app/services/flood_detection.py",
        "Backend/app/services/exposure_analysis.py",
        "Backend/app/services/gis_overlay.py",
        "scripts/generate_sample_data.py",
        "scripts/create_synthetic_tifs.py",
        "data/roads/roads.geojson",
        "data/boundaries/villages.geojson",
        "data/pois/facilities.geojson",
    ]
    
    logs = [f"Restoring map/GIS files from git commit {target_commit}...\n"]
    for fpath in files_to_restore:
        # Check git show
        res_show = subprocess.run(["git", "show", f"{target_commit}:{fpath}"], capture_output=True, text=True, cwd=r"c:\SatQuery")
        if res_show.returncode == 0 and res_show.stdout:
            full_path = os.path.join(r"c:\SatQuery", fpath.replace("/", os.sep))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8", newline="\n") as out_f:
                out_f.write(res_show.stdout)
            logs.append(f"[OK] Restored {fpath} ({len(res_show.stdout)} bytes)")
        else:
            logs.append(f"[FAIL] {fpath}: {res_show.stderr.strip()}")

    with open(log_file, "w", encoding="utf-8") as lf:
        lf.write("\n".join(logs))

if __name__ == "__main__":
    restore_commit()
