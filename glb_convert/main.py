import os
import json
from pathlib import Path
from dataclasses import dataclass
import trimesh
import numpy as np

@dataclass
class AircraftModel:
    name: str
    obj_files: list[str]
    airline_code: str = ""
    texture_file: str = ""
    aircraft_type: str = ""

def parse_xsb_file(file_path: str) -> list[AircraftModel]:
    models = []
    current_model = None
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('OBJ8_AIRCRAFT'):
                if current_model:
                    models.append(current_model)
                aircraft_code = line.split('_')[0].split()[-1]  
                current_model = AircraftModel(name="", obj_files=[], aircraft_type=aircraft_code)
            
            if not current_model:
                continue
                
            if 'OBJ8 SOLID YES' in line:
                obj_file = line.split('YES')[-1].strip().split(':')[-1].split('\\')[-1].strip()
                current_model.obj_files.append(obj_file)
            
            if 'AIRLINE' in line or 'LIVERY' in line:
                airline_code = line.split()[-1]  # 获取最后一个部分作为航司代码
                current_model.airline_code = airline_code
                current_model.name = f"{current_model.aircraft_type}_{airline_code}"

    
    if current_model:
        models.append(current_model)
    return models

def process_obj_file(obj_path: str) -> tuple[list, list, str]:
    vertices = []
    faces = []
    texture_file = None
    invalid_faces = 0
    uvs = []
    
    with open(obj_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('TEXTURE'):
                texture_file = line.split()[-1]
            elif line.startswith('VT'):
                parts = line.split()[1:]
                vertex = [float(x) for x in parts[:3]]
                vertices.append(vertex)
                # parts[6:8]
                if len(parts) >= 8:
                    uv = [float(parts[6]), float(parts[7])]
                    uvs.append(uv)
            elif line.startswith('IDX10'):
                parts = line.split()[1:]
                for idx in parts:
                    try:
                        faces.append(int(idx))
                    except ValueError:
                        print(f"Warning: Invalid face index in {obj_path}: {idx}")
                        continue

    vertex_count = len(vertices)
    grouped_faces = []
    num_face_triplets = len(faces) // 3
    
    for i in range(num_face_triplets):
        face_start = i * 3
        face = faces[face_start:face_start + 3]
        
        if all(0 <= idx < vertex_count for idx in face):
            grouped_faces.append(face)
        else:
            invalid_faces += 1
            continue

    if invalid_faces > 0:
        print(f"Warning: {obj_path}: Skipped {invalid_faces} faces with out-of-range indices (max vertex index: {vertex_count-1})")

    return vertices, grouped_faces, uv, texture_file

def merge_and_convert_to_glb(models: list[AircraftModel], input_dir: str, output_dir: str):
    for model in models:
        if not model.name:
            print(f"Warning: Skipping model with no name")
            continue

        print(f"Processing model: {model.name}")
        print(f"Input directory: {input_dir}")
        print(f"Output directory: {output_dir}")
        
        merged_vertices = []
        merged_faces = []
        textures = set()
        merged_uvs = []
        
        vertex_offset = 0
        
        for obj_file in model.obj_files:
            full_path = os.path.join(input_dir, obj_file)
            if not os.path.exists(full_path):
                print(f"Warning: File not found: {full_path}")
                continue
                
            try:
                vertices, faces, uvs, texture = process_obj_file(full_path)
                if texture:
                    textures.add(texture)
                
                if not vertices:
                    print(f"Warning: No vertices found in {obj_file}")
                    continue
                    
                if not faces:
                    print(f"Warning: No valid faces found in {obj_file}")
                    continue
                
                merged_vertices.extend(vertices)
                
                adjusted_faces = [[f + vertex_offset for f in face] for face in faces]
                merged_faces.extend(adjusted_faces)
                
                vertex_offset += len(vertices)
                
                merged_uvs.extend(uvs)
                
            except Exception as e:
                print(f"Error processing file {obj_file}: {str(e)}")
                continue

        if not merged_vertices or not merged_faces:
            print(f"Warning: No valid geometry found for model {model.name}")
            continue
            
        try:
            material = trimesh.visual.material.PBRMaterial()
            
            if textures:
                texture_path = os.path.join(input_dir, list(textures)[0])
                if os.path.exists(texture_path):
                    try:
                        import PIL.Image
                        image = PIL.Image.open(texture_path)
                        # Convert image to numpy array
                        image_data = np.array(image)
                        
                        material.baseColorTexture = image_data
                        material.baseColorFactor = [1.0, 1.0, 1.0, 1.0]
                    except Exception as e:
                        print(f"Error loading texture {texture_path}: {str(e)}")

            mesh = trimesh.Trimesh(
                vertices=np.array(merged_vertices),
                faces=np.array(merged_faces),
                visual=trimesh.visual.TextureVisuals(
                    material=material,
                    uv=np.array(merged_uvs)
                )
            )
            
            scene = trimesh.Scene([mesh])
            
            export_options = {
                'include_normals': True, 
                'merge_primitives': True
            }
            exported = trimesh.exchange.gltf.export_glb(
                scene, 
                unitize_normals=True
            )

            output_path = os.path.join(output_dir, f"{model.name}.glb")
            print(f"Attempting to export GLB to: {output_path}")
            try:
                import pyglet
                import collada
            except ImportError:
                print("Installing required dependencies...")
                import subprocess
                subprocess.check_call(["pip", "install", "pyglet", "pycollada"])

            scene = trimesh.Scene([mesh])
            exported = scene.export(file_type='glb')
            
            with open(output_path, 'wb') as f:
                f.write(exported)
            
            print(f"Successfully exported GLB file to {output_path}")
                    
        except Exception as e:
            print(f"Error exporting GLB for model {model.name}: {str(e)}")
            print(f"Vertices: {len(merged_vertices)}, Faces: {len(merged_faces)}")

def main():
    input_dir = '../static/planeModel'
    output_dir = '../static/model'
    
    for aircraft_dir in os.listdir(input_dir):
        aircraft_path = os.path.join(input_dir, aircraft_dir)
        if not os.path.isdir(aircraft_path):
            continue
            
        xsb_path = os.path.join(aircraft_path, 'xsb_aircraft.txt')
        if not os.path.exists(xsb_path):
            continue
        aircraft_output_dir = os.path.join(output_dir, aircraft_dir)
        os.makedirs(aircraft_output_dir, exist_ok=True)
        
        models = parse_xsb_file(xsb_path)
        merge_and_convert_to_glb(models, aircraft_path, aircraft_output_dir)
        
        mapping = {
            model.name: {
                "airline_code": model.airline_code,
                "aircraft_type": model.aircraft_type
            }
            for model in models 
            if model.name and model.airline_code
        }
        
        with open(os.path.join(aircraft_output_dir, 'livery_mapping.json'), 'w') as f:
            json.dump(mapping, f, indent=2)

if __name__ == '__main__':
    main()