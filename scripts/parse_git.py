import os
import zlib

def read_object(sha):
    path = os.path.join(r"c:\SatQuery\.git\objects", sha[:2], sha[2:])
    if not os.path.exists(path):
        return None, None
    with open(path, "rb") as f:
        data = zlib.decompress(f.read())
    header, content = data.split(b"\x00", 1)
    obj_type, size_str = header.split(b" ")
    return obj_type.decode("utf-8"), content

def parse_tree(content):
    entries = []
    idx = 0
    while idx < len(content):
        mode_end = content.find(b" ", idx)
        mode = content[idx:mode_end].decode("utf-8")
        name_end = content.find(b"\x00", mode_end)
        name = content[mode_end+1:name_end].decode("utf-8")
        sha = content[name_end+1:name_end+21].hex()
        entries.append((mode, name, sha))
        idx = name_end + 21
    return entries

def extract_tree_recursive(tree_sha, target_dir):
    obj_type, content = read_object(tree_sha)
    if obj_type != "tree":
        return
    entries = parse_tree(content)
    for mode, name, sha in entries:
        out_path = os.path.join(target_dir, name)
        sub_type, sub_content = read_object(sha)
        if sub_type == "blob":
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(sub_content)
            print(f"Extracted blob: {out_path} ({len(sub_content)} bytes)")
        elif sub_type == "tree":
            extract_tree_recursive(sha, out_path)

commit_sha = "d2b76003bb523e3cf842c5297c8187cef0f1ef17"
obj_type, content = read_object(commit_sha)
print("Commit object type:", obj_type)
tree_sha = content.decode("utf-8").split("\n")[0].split(" ")[1]
print("Tree SHA for d2b7600:", tree_sha)

# We want to restore map/GIS files: MapViewer.jsx, polygon_generation.py, flood_detection.py, generate_sample_data.py, create_synthetic_tifs.py, roads.geojson
# Let's extract tree recursive to a temp dir or target paths
target_files = [
    "Frontend/src/components/MapViewer.jsx",
    "Backend/app/services/polygon_generation.py",
    "Backend/app/services/flood_detection.py",
    "Backend/app/services/exposure_analysis.py",
    "Backend/app/services/gis_overlay.py",
    "scripts/generate_sample_data.py",
    "scripts/create_synthetic_tifs.py",
    "data/roads/roads.geojson",
]

def find_sha_in_tree(tree_sha, path_parts):
    obj_type, content = read_object(tree_sha)
    if obj_type != "tree":
        return None
    entries = parse_tree(content)
    target_name = path_parts[0]
    for mode, name, sha in entries:
        if name == target_name:
            if len(path_parts) == 1:
                return sha
            else:
                return find_sha_in_tree(sha, path_parts[1:])
    return None

for rel_path in target_files:
    parts = rel_path.split("/")
    blob_sha = find_sha_in_tree(tree_sha, parts)
    if blob_sha:
        b_type, b_content = read_object(blob_sha)
        if b_type == "blob":
            dest_path = os.path.join(r"c:\SatQuery", rel_path.replace("/", os.sep))
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(b_content)
            print(f"[RESTORED] {rel_path} -> {len(b_content)} bytes")
        else:
            print(f"[WARN] {rel_path} blob SHA {blob_sha} is type {b_type}")
    else:
        print(f"[NOT FOUND] {rel_path} in tree {tree_sha}")
