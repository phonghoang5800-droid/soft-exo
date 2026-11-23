# Soft-Exo — Procedural 3D Soft Exoskeleton & Gazebo Simulation

[![Blender](https://img.shields.io/badge/Blender-5.x_Python_API-F5792A?logo=blender&logoColor=white)](https://www.blender.org/)
[![Simulation](https://img.shields.io/badge/Physics-Gazebo_SDF-1d4ed8)](#repository-contents)

A procedural 3D design and physics simulation workspace for a soft-exoskeleton wearable concept, combining Blender Python scene generation (`soft_exo_stage_01_to_05.py`) with Gazebo SDF robotics simulation assets (`soft_exo.sdf`).

## Pipeline Stages (`soft_exo_stage_01_to_05.py`)

The canonical Blender Python script programmatically resets and constructs five iterative visual and physics stages:

1. **Stage 1 (`01_without_assist` / `01_with_assist.blend`):** Base anatomical & garment assembly.
2. **Stage 2 (`02_with_assist.blend`):** Soft-assist actuation layout.
3. **Stage 3 (`03_with_assist_glow.blend`):** Emissive visual feedback cues for actuation state.
4. **Stage 4 (`04_with_assist_ui.blend`):** Interactive overlay & UI indicators.
5. **Stage 5 (`05_physics.blend` – `08_hardware_link.blend`):** Contact/physics handlers and hardware linkage iterations.

## Repository Contents

```text
soft-exo/
├── soft_exo_stage_01_to_05.py   # Canonical Blender 5.x procedural generation script
├── 01_with_assist.blend ... 08_hardware_link.blend
├── soft_exo.sdf                 # Gazebo SDF physics model definition
├── soft_exo_gazebo.zip          # Gazebo simulation package
└── app soft exo.zip             # Companion prototype package
```

## Author

**Nguyen Hoang Phong** — [Portfolio](https://phonghoang5800-droid.github.io) · [GitHub](https://github.com/phonghoang5800-droid)
