import os
import json
from pathlib import Path
import numpy as np
import trimesh
import pygltflib
from PIL import Image
import shutil
import base64
import io

class XPlaneMaterial:
    def __init__(self):
        self.texture_path = None
        self.diffuse = [1.0, 1.0, 1.0]
        self.ambient = [0.0, 0.0, 0.0]
        self.specular = [0.0, 0.0, 0.0]

class XPlaneOBJ:
    def __init__(self):
        self.vertices = []
        self.normals = []
        self.uvs = []
        self.indices = []
        self.texture_path = None
        self.materials = []
        self.current_material = None

    def parse_file(self, filepath):
        print(f"Parsing file: {filepath}")  # Debug log
        with open(filepath, 'r') as f:
            lines = f.readlines()
            
        current_indices = []
        line_number = 0
            
        for line in lines:
            line_number += 1
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            parts = line.split()
            if not parts:
                continue
                
            cmd = parts[0]
            
            try:
                if cmd == 'VT':
                    if len(parts) < 6:
                        print(f"Warning: Invalid VT line {line_number}: {line}")
                        continue
                    self.vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                    self.uvs.append([float(parts[4]), float(parts[5])])
                elif cmd == 'IDX':
                    if len(parts) < 2:
                        print(f"Warning: Invalid IDX line {line_number}: {line}")
                        continue
                    new_indices = [int(idx) for idx in parts[1:]]
                    current_indices.extend(new_indices)
                    
                    # When we have enough indices to form complete triangles
                    while len(current_indices) >= 3:
                        self.indices.extend(current_indices[:3])
                        current_indices = current_indices[3:]
                elif cmd == 'TEXTURE':
                    material = XPlaneMaterial()
                    material.texture_path = parts[1]
                    self.materials.append(material)
                    self.current_material = material
                    self.texture_path = parts[1]
            except Exception as e:
                print(f"Error parsing line {line_number}: {line}")
                print(f"Error details: {str(e)}")
                continue
                
        # Debug information
        print(f"Parsed {len(self.vertices)} vertices")
        print(f"Parsed {len(self.indices)} indices")
        print(f"Parsed {len(self.uvs)} UV coordinates")
        if self.texture_path:
            print(f"Found texture: {self.texture_path}")

class ModelConverter:
    def __init__(self, input_dir, output_dir):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        
    def process_models(self):
        for aircraft_dir in self.input_dir.iterdir():
            if not aircraft_dir.is_dir():
                continue
                
            aircraft_type = aircraft_dir.name
            xsb_file = aircraft_dir / "xsb_aircraft.txt"
            
            if not xsb_file.exists():
                continue
                
            out_aircraft_dir = self.output_dir / aircraft_type
            out_aircraft_dir.mkdir(parents=True, exist_ok=True)
            
            airline_mapping = self.process_aircraft_file(xsb_file, aircraft_dir, out_aircraft_dir)
            
            # 保存airline mapping
            self.save_airline_mapping(out_aircraft_dir, airline_mapping)
    
    def process_aircraft_file(self, xsb_file, aircraft_dir, out_dir):
        airline_mapping = {}
        current_model = None
        
        with open(xsb_file, 'r') as f:
            content = f.read()
            models = content.split('\n\n')
            
            for model in models:
                if not model.strip():
                    continue
                    
                obj_files = []
                textures = set()
                airline_code = None
                
                for line in model.split('\n'):
                    if line.startswith('OBJ8 SOLID YES'):
                        obj_path = line.split()[-1]
                        if ':' in obj_path:
                            obj_path = obj_path.split(':')[-1]
                        if '\\' in obj_path:
                            obj_path = obj_path.split('\\')[-1]
                        obj_files.append(aircraft_dir / obj_path)
                    
                    elif line.startswith(('AIRLINE', 'LIVERY')):
                        parts = line.split()
                        if len(parts) >= 3:
                            airline_code = parts[-1]
                
                if airline_code and obj_files:
                    textures = self.extract_textures(obj_files)
                    
                    # 合并
                    glb_filename = f"{airline_code}.glb"
                    self.convert_to_glb(obj_files, textures, out_dir / glb_filename)
                    airline_mapping[airline_code] = {
                        'model': glb_filename,
                        'textures': list(textures)
                    }
        
        return airline_mapping
    
    def extract_textures(self, obj_files):
        textures = set()
        for obj_file in obj_files:
            with open(obj_file, 'r') as f:
                for line in f:
                    if line.startswith('TEXTURE'):
                        texture = line.split()[-1]
                        textures.add(texture)
        return textures

    def convert_xplane_to_standard_obj(self, obj_file):
        try:
            xplane_obj = XPlaneOBJ()
            xplane_obj.parse_file(obj_file)
            
            if not xplane_obj.vertices:
                print(f"Warning: No vertices found in {obj_file}")
                return None, xplane_obj.texture_path
                
            if not xplane_obj.indices:
                print(f"Warning: No indices found in {obj_file}")
                return None, xplane_obj.texture_path
                
            if len(xplane_obj.indices) % 3 != 0:
                print(f"Warning: Number of indices ({len(xplane_obj.indices)}) is not divisible by 3 in {obj_file}")
                return None, xplane_obj.texture_path
                
            vertices = np.array(xplane_obj.vertices)
            faces = np.array(xplane_obj.indices).reshape(-1, 3)
            uvs = np.array(xplane_obj.uvs)
            
            if len(vertices) == 0:
                print(f"Warning: Empty vertices array in {obj_file}")
                return None, xplane_obj.texture_path
                
            if len(faces) == 0:
                print(f"Warning: Empty faces array in {obj_file}")
                return None, xplane_obj.texture_path
                
            try:
                mesh = trimesh.Trimesh(
                    vertices=vertices,
                    faces=faces,
                    visual=trimesh.visual.TextureVisuals(
                        uv=uvs
                    )
                )
                return mesh, xplane_obj.texture_path
            except Exception as e:
                print(f"Error creating trimesh for {obj_file}: {e}")
                return None, xplane_obj.texture_path
                
        except Exception as e:
            print(f"Error processing {obj_file}: {e}")
            return None, xplane_obj.texture_path

    def merge_meshes(self, meshes):
        if not meshes:
            return None
        
        if len(meshes) == 1:
            return meshes[0]
            
        vertices = []
        faces = []
        uvs = []
        materials = []
        
        vertex_offset = 0
        for mesh in meshes:
            vertices.extend(mesh.vertices)
            faces.extend(mesh.faces + vertex_offset)
            uvs.extend(mesh.visual.uv)
            vertex_offset += len(mesh.vertices)
            if hasattr(mesh.visual, 'material'):
                materials.append(mesh.visual.material)
            
        return trimesh.Trimesh(
            vertices=np.array(vertices),
            faces=np.array(faces),
            visual=trimesh.visual.TextureVisuals(
                uv=np.array(uvs)
            )
        )

    def convert_to_glb(self, obj_files, textures, output_path):
        meshes = []
        
        for obj_file in obj_files:
            result = self.convert_xplane_to_standard_obj(obj_file)
            if result is None:
                continue
            mesh, texture_info = result
            if mesh is not None:
                if texture_info:
                    texture_path = self.input_dir / texture_info
                    if texture_path.exists():
                        try:
                            with Image.open(texture_path) as img:
                                # 转换RGBA
                                if img.mode != 'RGBA':
                                    img = img.convert('RGBA')
                                material = trimesh.visual.material.PBRMaterial(
                                    baseColorTexture=img
                                )
                                mesh.visual = trimesh.visual.TextureVisuals(
                                    material=material,
                                    uv=mesh.visual.uv
                                )
                        except Exception as e:
                            print(f"Error processing texture {texture_path}: {e}")
                meshes.append(mesh)

        if not meshes:
            print(f"Warning: No valid meshes to convert for {output_path}")
            return

        if len(meshes) > 1:
            final_mesh = meshes[0]
            for mesh in meshes[1:]:
                final_mesh = trimesh.util.concatenate([final_mesh, mesh])
        else:
            final_mesh = meshes[0]

        scene = trimesh.Scene()
        scene.add_geometry(final_mesh)

        try:
            glb_export = trimesh.exchange.gltf.export_glb(
                scene,
                include_normals=True
            )
            
            # 保存到glb文件
            with open(output_path, 'wb') as f:
                f.write(glb_export)
                
        except Exception as e:
            print(f"Error exporting GLB for {output_path}: {e}")
            import traceback
            traceback.print_exc()
            return

    def save_airline_mapping(self, out_dir, mapping):
        with open(out_dir / 'airline_mapping.json', 'w') as f:
            json.dump(mapping, f, indent=2)

def main():
    input_dir = "../static/planeModel"
    output_dir = "../static/model"
    
    converter = ModelConverter(input_dir, output_dir)
    converter.process_models()

if __name__ == "__main__":
    main()
