import bpy
import math
from mathutils import Vector

# ============================================================
# SOFT-EXO FASHION - CANONICAL PIPELINE 01 -> 05
# Blender 5.x
#
# Chỉ sửa STAGE rồi Run Script:
#   1 = 01_without_assist.blend
#   2 = 02_with_assist.blend
#   3 = 03_with_assist_glow.blend
#   4 = 04_with_assist_ui.blend
#   5 = 05_physics.blend
#
# Mỗi lần chạy script sẽ RESET TOÀN BỘ SCENE.
# ============================================================

STAGE = 5

if STAGE not in {1, 2, 3, 4, 5}:
    raise ValueError("STAGE phải là 1, 2, 3, 4 hoặc 5")

# ============================================================
# 0) RESET
# ============================================================

# Xóa handler cũ để tránh chạy chồng khi Run Script nhiều lần.
for handler in list(bpy.app.handlers.frame_change_post):
    if getattr(handler, "__name__", "") == "soft_exo_contact_update":
        bpy.app.handlers.frame_change_post.remove(handler)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.render.fps = 24
scene.frame_start = 1

FPS = 24

# ============================================================
# 1) THÔNG SỐ GAIT
# ============================================================

# STAGE 1: người cao tuổi chưa trợ lực, đi chậm, bước ngắn, khuỵu/còng rõ hơn.
if STAGE == 1:
    STEP_LENGTH = 0.32
    CADENCE = 48.0
    DOUBLE_SUPPORT = 0.20
    SWING_CLEARANCE = 0.025
    HIP_X = 0.16
    HIP_Z_MID = 0.930
    LOWER_SPINE_LEAN = -11.0
    UPPER_SPINE_LEAN = -8.0
    HEAD_FORWARD = 0.055
    ARM_SWING = 2.5
else:
    # STAGE 2+: có Soft-Exo, bước cải thiện nhẹ nhưng vẫn là gait người cao tuổi.
    STEP_LENGTH = 0.42
    CADENCE = 56.0
    DOUBLE_SUPPORT = 0.16
    SWING_CLEARANCE = 0.035
    HIP_X = 0.15
    HIP_Z_MID = 0.955
    LOWER_SPINE_LEAN = -7.0
    UPPER_SPINE_LEAN = -4.0
    HEAD_FORWARD = 0.035
    ARM_SWING = 4.0

STEP_FRAMES = max(12, round((60.0 / CADENCE) * FPS))

THIGH_LEN = 0.47
SHIN_LEN = 0.45
HIP_LOCAL_Z = -0.035
ROOT_Z_MID = HIP_Z_MID - HIP_LOCAL_Z

FOOT_LENGTH = 0.30
FOOT_WIDTH = 0.19
FOOT_T = 0.065
FOOT_CENTER_Y = 0.055

# Đi thẳng. Stage 5 đi ít bước phẳng hơn để tiến tới cầu thang.
FLAT_STEPS = 14 if STAGE < 5 else 10

# Lưu các khoảng frame chân được trợ để Stage 3/4/5 dùng glow/UI.
assist_intervals = []  # list[(start_frame, end_frame, "LEFT"|"RIGHT", mode)]

# ============================================================
# 2) MATERIAL HELPERS
# ============================================================

def make_mat(name, rgb, metallic=0.0, roughness=0.45):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    mat.metallic = metallic
    mat.roughness = roughness
    return mat

MAT_BODY = make_mat("Body", (0.48, 0.49, 0.51), 0.0, 0.65)
MAT_CLOTH = make_mat("Clothing", (0.10, 0.12, 0.16), 0.05, 0.65)
MAT_EXO = make_mat("SoftExo", (0.02, 0.17, 0.72), 0.65, 0.23)
MAT_JOINT = make_mat("Actuator", (0.018, 0.020, 0.026), 0.82, 0.18)
MAT_SHOE = make_mat("Shoe", (0.03, 0.034, 0.04), 0.25, 0.45)
MAT_ROAD = make_mat("Road", (0.09, 0.10, 0.12), 0.0, 0.82)
MAT_LINE = make_mat("RoadLine", (0.38, 0.40, 0.44), 0.0, 0.60)
MAT_STEP = make_mat("Stair", (0.23, 0.25, 0.30), 0.10, 0.60)
MAT_CONTACT_OFF = make_mat("MAT_CONTACT_OFF", (0.08, 0.08, 0.08), 0.0, 0.70)
MAT_CONTACT_ON = make_mat("MAT_CONTACT_ON", (0.05, 0.90, 0.18), 0.0, 0.35)

# ============================================================
# 3) OBJECT HELPERS
# ============================================================

def add_bevel(obj, width=0.02):
    mod = obj.modifiers.new(name="Rounded", type='BEVEL')
    mod.width = width
    mod.segments = 3


def add_cube(name, parent, loc, dims, mat, rounded=0.02):
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    obj.name = name
    if parent is not None:
        obj.parent = parent
    obj.location = loc
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rounded > 0:
        add_bevel(obj, rounded)
    obj.data.materials.append(mat)
    return obj


def add_cylinder(name, parent, loc, radius, depth, mat, horizontal=False):
    rot = (0.0, math.radians(90.0), 0.0) if horizontal else (0.0, 0.0, 0.0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    if parent is not None:
        obj.parent = parent
    obj.location = loc
    add_bevel(obj, 0.01)
    obj.data.materials.append(mat)
    return obj


def add_sphere(name, parent, loc, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16)
    obj = bpy.context.object
    obj.name = name
    if parent is not None:
        obj.parent = parent
    obj.location = loc
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def add_pivot(name, parent, loc):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    obj.location = loc
    obj.rotation_mode = 'XYZ'
    obj.empty_display_type = 'SPHERE'
    obj.empty_display_size = 0.025
    return obj


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def key_rot(obj, frame, x=0.0, y=0.0, z=0.0):
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = (x, y, z)
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def key_root(frame, x, y, z, yaw=0.0, pelvis_roll=0.0, pelvis_twist=0.0):
    ROOT.location = (x, y, z)
    ROOT.rotation_mode = 'XYZ'
    ROOT.rotation_euler = (0.0, pelvis_roll, yaw + pelvis_twist)
    ROOT.keyframe_insert(data_path="location", frame=frame)
    ROOT.keyframe_insert(data_path="rotation_euler", frame=frame)

# ============================================================
# 4) DỰNG NGƯỜI + SOFT-EXO
# ============================================================

ROOT = add_pivot("SOFT_EXO_ROOT", None, (0.0, -STEP_LENGTH / 2.0, ROOT_Z_MID))

add_cube("PELVIS", ROOT, (0, 0, 0.025), (0.36, 0.22, 0.18), MAT_CLOTH, 0.045)
add_cube("EXO_WAIST", ROOT, (0, 0, -0.015), (0.46, 0.28, 0.105), MAT_EXO, 0.035)
add_cube("CONTROL_UNIT", ROOT, (0, -0.15, 0.055), (0.17, 0.075, 0.18), MAT_JOINT, 0.025)

LOWER_SPINE = add_pivot("LOWER_SPINE", ROOT, (0, 0, 0.09))
UPPER_SPINE = add_pivot("UPPER_SPINE", LOWER_SPINE, (0, 0, 0.34))
add_cube("LOWER_TORSO", LOWER_SPINE, (0, 0, 0.18), (0.34, 0.21, 0.34), MAT_CLOTH, 0.06)
add_cube("UPPER_TORSO", UPPER_SPINE, (0, 0, 0.18), (0.39, 0.22, 0.36), MAT_CLOTH, 0.07)
add_cylinder("NECK", UPPER_SPINE, (0, 0.015, 0.42), 0.055, 0.11, MAT_BODY)
add_sphere("HEAD", UPPER_SPINE, (0, HEAD_FORWARD, 0.57), (0.125, 0.115, 0.155), MAT_BODY)


def build_arm(side, x):
    shoulder = add_pivot(f"{side}_SHOULDER", UPPER_SPINE, (x, 0, 0.31))
    add_cube(f"{side}_UPPER_ARM", shoulder, (0, 0, -0.18), (0.085, 0.085, 0.36), MAT_CLOTH, 0.035)
    elbow = add_pivot(f"{side}_ELBOW", shoulder, (0, 0, -0.36))
    add_cube(f"{side}_FOREARM", elbow, (0, 0.025, -0.16), (0.072, 0.072, 0.32), MAT_BODY, 0.03)
    add_sphere(f"{side}_HAND", elbow, (0, 0.05, -0.35), (0.055, 0.045, 0.07), MAT_BODY)
    return shoulder, elbow


L_SHOULDER, L_ELBOW = build_arm("LEFT", -0.24)
R_SHOULDER, R_ELBOW = build_arm("RIGHT", 0.24)


def build_leg(side, x):
    hip = add_pivot(f"{side}_HIP", ROOT, (x, 0, HIP_LOCAL_Z))
    add_cylinder(f"{side}_HIP_MOTOR", hip, (0, 0, 0), 0.083, 0.105, MAT_JOINT, True)
    add_cylinder(f"{side}_THIGH", hip, (0, 0, -THIGH_LEN / 2), 0.070, THIGH_LEN * 0.93, MAT_BODY)
    rail_x = -0.085 if side == "LEFT" else 0.085
    add_cube(f"{side}_EXO_THIGH", hip, (rail_x, 0, -THIGH_LEN / 2), (0.040, 0.047, THIGH_LEN * 0.85), MAT_EXO, 0.012)

    knee = add_pivot(f"{side}_KNEE", hip, (0, 0, -THIGH_LEN))
    add_cylinder(f"{side}_KNEE_MOTOR", knee, (0, 0, 0), 0.098, 0.115, MAT_JOINT, True)
    add_cylinder(f"{side}_SHIN", knee, (0, 0, -SHIN_LEN / 2), 0.060, SHIN_LEN * 0.93, MAT_BODY)
    add_cube(f"{side}_EXO_SHIN", knee, (rail_x, 0, -SHIN_LEN / 2), (0.035, 0.043, SHIN_LEN * 0.84), MAT_EXO, 0.010)

    ankle = add_pivot(f"{side}_ANKLE", knee, (0, 0, -SHIN_LEN))
    add_cylinder(f"{side}_ANKLE_JOINT", ankle, (0, 0, 0), 0.060, 0.085, MAT_JOINT, True)
    foot = add_cube(f"{side}_FOOT", ankle, (0, FOOT_CENTER_Y, -FOOT_T / 2), (FOOT_WIDTH, FOOT_LENGTH, FOOT_T), MAT_SHOE, 0.022)
    return hip, knee, ankle, foot


L_HIP, L_KNEE, L_ANKLE, LEFT_FOOT = build_leg("LEFT", -HIP_X)
R_HIP, R_KNEE, R_ANKLE, RIGHT_FOOT = build_leg("RIGHT", HIP_X)

# ============================================================
# 5) IK CHÂN
# ============================================================

def solve_leg(foot_y_world, foot_z_world, root_y, root_z, direction=1):
    hip_z = root_z + HIP_LOCAL_Z
    forward = direction * (foot_y_world - root_y)
    down = hip_z - foot_z_world

    r2 = forward * forward + down * down
    cos_q = (r2 - THIGH_LEN ** 2 - SHIN_LEN ** 2) / (2.0 * THIGH_LEN * SHIN_LEN)
    cos_q = max(-0.9999, min(0.9999, cos_q))
    q = math.acos(cos_q)

    hip = math.atan2(forward, down) + math.atan2(
        SHIN_LEN * math.sin(q),
        THIGH_LEN + SHIN_LEN * math.cos(q)
    )
    knee = -q
    return hip, knee, q


def apply_leg_pose(side, frame, foot_y, foot_z, foot_pitch, root_y, root_z, direction=1):
    hip, knee, q = solve_leg(foot_y, foot_z, root_y, root_z, direction)
    ankle = foot_pitch - hip + q
    if side == "LEFT":
        key_rot(L_HIP, frame, hip)
        key_rot(L_KNEE, frame, knee)
        key_rot(L_ANKLE, frame, ankle)
    else:
        key_rot(R_HIP, frame, hip)
        key_rot(R_KNEE, frame, knee)
        key_rot(R_ANKLE, frame, ankle)

# ============================================================
# 6) BODY MOTION
# ============================================================

def animate_upper_body(frame, phase, stair=False):
    stair_extra_low = -3.0 if stair else 0.0
    stair_extra_up = -2.0 if stair else 0.0

    low = math.radians(LOWER_SPINE_LEAN + stair_extra_low - 0.5 * math.sin(phase))
    up = math.radians(UPPER_SPINE_LEAN + stair_extra_up - 0.3 * math.sin(phase))
    key_rot(LOWER_SPINE, frame, low)
    key_rot(UPPER_SPINE, frame, up)

    arm = math.radians(ARM_SWING * math.sin(phase))
    key_rot(L_SHOULDER, frame, -arm)
    key_rot(R_SHOULDER, frame, arm)
    key_rot(L_ELBOW, frame, math.radians(-18.0))
    key_rot(R_ELBOW, frame, math.radians(-18.0))

# ============================================================
# 7) FLAT WALK
# ============================================================

left_y = 0.0
right_y = -STEP_LENGTH
left_z = FOOT_T
right_z = FOOT_T
frame = 1


def walk_one_step(frame, left_y, right_y, step_length, step_frames, mode="WALK"):
    # Hướng +Y. Chân có Y nhỏ hơn là chân phía sau và sẽ swing.
    swing_left = left_y < right_y
    if swing_left:
        swing_old = left_y
        stance_y = right_y
        swing_new = stance_y + step_length
    else:
        swing_old = right_y
        stance_y = left_y
        swing_new = stance_y + step_length

    old_mid = (left_y + right_y) / 2.0
    new_left = swing_new if swing_left else left_y
    new_right = right_y if swing_left else swing_new
    new_mid = (new_left + new_right) / 2.0

    start = frame
    end = frame + step_frames - 1
    assist_intervals.append((start, end, "LEFT" if swing_left else "RIGHT", mode))

    for f in range(step_frames):
        u = f / max(1, step_frames - 1)
        s = smoothstep(u)
        current = frame + f

        root_y = old_mid + (new_mid - old_mid) * s
        root_z = ROOT_Z_MID + 0.003 * math.sin(math.pi * u)
        stance_side = 1.0 if swing_left else -1.0
        root_x = stance_side * 0.022 * (math.sin(math.pi * u) ** 2)

        # Chân swing giữ dưới đất ở đầu/cuối bước lâu hơn (double support).
        if u < DOUBLE_SUPPORT:
            sy = swing_old
            sz = FOOT_T
            spitch = 0.0
        elif u > 1.0 - DOUBLE_SUPPORT:
            sy = swing_new
            sz = FOOT_T
            spitch = math.radians(2.5)
        else:
            p = (u - DOUBLE_SUPPORT) / (1.0 - 2.0 * DOUBLE_SUPPORT)
            ps = smoothstep(p)
            sy = swing_old + (swing_new - swing_old) * ps
            sz = FOOT_T + SWING_CLEARANCE * (math.sin(math.pi * p) ** 1.15)
            spitch = math.radians(2.0 * math.sin(math.pi * p))

        if swing_left:
            ly, lz, lp = sy, sz, spitch
            ry, rz, rp = stance_y, FOOT_T, 0.0
        else:
            ly, lz, lp = stance_y, FOOT_T, 0.0
            ry, rz, rp = sy, sz, spitch

        apply_leg_pose("LEFT", current, ly, lz, lp, root_y, root_z, 1)
        apply_leg_pose("RIGHT", current, ry, rz, rp, root_y, root_z, 1)

        phase = 2.0 * math.pi * current / max(1, STEP_FRAMES * 2)
        animate_upper_body(current, phase, stair=False)

        pelvis_roll = math.radians(1.0 * stance_side * (math.sin(math.pi * u) ** 2))
        pelvis_twist = math.radians(1.0 * math.sin(phase))
        key_root(current, root_x, root_y, root_z, 0.0, pelvis_roll, pelvis_twist)

    return frame + step_frames, new_left, new_right


for _ in range(FLAT_STEPS):
    frame, left_y, right_y = walk_one_step(frame, left_y, right_y, STEP_LENGTH, STEP_FRAMES, "WALK")

# ============================================================
# 8) ROAD / CAMERA
# ============================================================

# Stage 1-4 chỉ cần đường phẳng. Stage 5 sẽ kéo dài nền tới cầu thang.
flat_end_y = max(left_y, right_y) + 1.0
road_start_y = -1.2
road_len = flat_end_y - road_start_y
road_center_y = (flat_end_y + road_start_y) / 2.0

ROAD = add_cube("ROAD", None, (0, road_center_y, -0.035), (2.2, road_len, 0.07), MAT_ROAD, 0.012)

mark_y = road_start_y + 0.4
idx = 0
while mark_y < flat_end_y:
    add_cube(f"ROAD_MARK_{idx}", None, (0, mark_y, 0.006), (1.85, 0.022, 0.012), MAT_LINE, 0.0)
    mark_y += 0.50
    idx += 1

bpy.ops.object.light_add(type='SUN', location=(3.0, -3.0, 6.0))
sun = bpy.context.object
sun.name = "SUN"
sun.data.energy = 2.0
sun.rotation_euler = (math.radians(25.0), math.radians(-20.0), math.radians(-25.0))

CAM_TARGET = add_pivot("CAM_TARGET", ROOT, (0.0, 0.55, 0.38))
bpy.ops.object.camera_add()
cam = bpy.context.object
cam.name = "FOLLOW_CAMERA"
cam.parent = ROOT
cam.location = (2.1, -3.2, 1.45)
track = cam.constraints.new(type='TRACK_TO')
track.target = CAM_TARGET
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'
cam.data.lens = 55
scene.camera = cam

# ============================================================
# 9) STAGE 3+ : GLOW
# ============================================================

LEFT_EXO_OBJECTS = [bpy.data.objects.get("LEFT_EXO_THIGH"), bpy.data.objects.get("LEFT_EXO_SHIN")]
RIGHT_EXO_OBJECTS = [bpy.data.objects.get("RIGHT_EXO_THIGH"), bpy.data.objects.get("RIGHT_EXO_SHIN")]


def make_glow_material(name):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.01, 0.05, 0.22, 1.0)
    if bsdf.inputs.get("Metallic"):
        bsdf.inputs["Metallic"].default_value = 0.65
    if bsdf.inputs.get("Roughness"):
        bsdf.inputs["Roughness"].default_value = 0.22

    emission_color = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
    emission_strength = bsdf.inputs.get("Emission Strength")
    if emission_color is not None:
        emission_color.default_value = (0.01, 0.25, 1.0, 1.0)
    if emission_strength is None:
        raise RuntimeError("Không tìm thấy Emission Strength trong Principled BSDF")
    emission_strength.default_value = 0.15
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, emission_strength


def assign_material(objects, material):
    for obj in objects:
        if obj is not None:
            obj.data.materials.clear()
            obj.data.materials.append(material)


def glow_key(socket, frame_number, value):
    socket.default_value = value
    socket.keyframe_insert(data_path="default_value", frame=frame_number)


LEFT_GLOW_MAT = RIGHT_GLOW_MAT = None
LEFT_STRENGTH = RIGHT_STRENGTH = None

if STAGE >= 3:
    LEFT_GLOW_MAT, LEFT_STRENGTH = make_glow_material("LEFT_ASSIST_GLOW")
    RIGHT_GLOW_MAT, RIGHT_STRENGTH = make_glow_material("RIGHT_ASSIST_GLOW")
    assign_material(LEFT_EXO_OBJECTS, LEFT_GLOW_MAT)
    assign_material(RIGHT_EXO_OBJECTS, RIGHT_GLOW_MAT)

# ============================================================
# 10) STAGE 4+ : UI
# ============================================================

def make_camera_text(name, body, x, y, z, size):
    bpy.ops.object.text_add()
    txt = bpy.context.object
    txt.name = name
    txt.data.body = body
    txt.data.align_x = 'CENTER'
    txt.data.align_y = 'CENTER'
    txt.data.size = size
    txt.data.extrude = 0.004
    txt.parent = cam
    txt.location = (x, y, z)
    txt.rotation_euler = (math.radians(90), 0, 0)
    return txt


TITLE_TEXT = AI_TEXT = LEFT_TEXT = RIGHT_TEXT = None

if STAGE >= 4:
    TITLE_TEXT = make_camera_text("UI_TITLE", "WITH SOFT-EXO ASSIST", 0.0, -1.8, 0.88, 0.11)
    AI_TEXT = make_camera_text("UI_AI", "AI GAIT DETECTION: ACTIVE", 0.0, -1.8, 0.72, 0.060)
    LEFT_TEXT = make_camera_text("UI_LEFT", "LEFT LEG ASSIST", -0.72, -1.8, -0.72, 0.070)
    RIGHT_TEXT = make_camera_text("UI_RIGHT", "RIGHT LEG ASSIST", 0.72, -1.8, -0.72, 0.070)


def visibility_key(obj, frame_number, visible):
    obj.hide_render = not visible
    obj.hide_viewport = not visible
    obj.keyframe_insert(data_path="hide_render", frame=frame_number)
    obj.keyframe_insert(data_path="hide_viewport", frame=frame_number)

# ============================================================
# 11) STAGE 5 : PHYSICS + STAIRS + CONTACT
# ============================================================

LEFT_SENSOR = RIGHT_SENSOR = None
CONTACT_TOLERANCE = 0.015


def make_passive(obj, friction=0.9, restitution=0.01):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.rigidbody.object_add()
    obj.rigid_body.type = 'PASSIVE'
    obj.rigid_body.collision_shape = 'BOX'
    obj.rigid_body.friction = friction
    obj.rigid_body.restitution = restitution
    obj.select_set(False)


if STAGE >= 5:
    # 11A) Đưa cầu thang ngay sau đoạn đi phẳng.
    STAIR_COUNT = 5
    STAIR_HEIGHT = 0.14
    STAIR_DEPTH = 0.32
    STAIR_STEP_FRAMES = 42
    STAIR_CLEARANCE = 0.080
    PAUSE_FRAMES = 24

    front_y = max(left_y, right_y)
    FIRST_STAIR_Y = front_y + 0.38
    TOP_HEIGHT = STAIR_COUNT * STAIR_HEIGHT

    # Kéo nền tới hết cầu thang.
    stair_end_y = FIRST_STAIR_Y + (STAIR_COUNT + 2) * STAIR_DEPTH + 0.8
    ROAD.dimensions.y = stair_end_y - road_start_y
    ROAD.location.y = (stair_end_y + road_start_y) / 2.0
    bpy.context.view_layer.objects.active = ROAD
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    make_passive(ROAD, 0.85, 0.02)

    stairs = []
    for i in range(STAIR_COUNT):
        h = STAIR_HEIGHT * (i + 1)
        y = FIRST_STAIR_Y + i * STAIR_DEPTH
        stair = add_cube(
            f"CLIMB_STAIR_{i+1}", None,
            (0.0, y, h / 2.0),
            (1.8, STAIR_DEPTH, h),
            MAT_STEP, 0.01
        )
        make_passive(stair, 0.95, 0.01)
        stairs.append(stair)

    landing_y = FIRST_STAIR_Y + STAIR_COUNT * STAIR_DEPTH + 0.35
    landing = add_cube(
        "CLIMB_LANDING", None,
        (0.0, landing_y, TOP_HEIGHT / 2.0),
        (1.8, 0.70, TOP_HEIGHT),
        MAT_STEP, 0.01
    )
    make_passive(landing, 0.95, 0.01)

    # Dốc test đặt bên cạnh, không cắt đường chính.
    ramp = add_cube(
        "PHYSICS_RAMP", None,
        (3.0, FIRST_STAIR_Y + 0.6, 0.24),
        (1.6, 3.0, 0.12),
        MAT_STEP, 0.01
    )
    ramp.rotation_euler[0] = math.radians(10.0)
    make_passive(ramp, 0.90, 0.01)

    # 11B) Dừng trước cầu thang.
    root_y = (left_y + right_y) / 2.0
    for f in range(PAUSE_FRAMES):
        current = frame + f
        apply_leg_pose("LEFT", current, left_y, FOOT_T, 0.0, root_y, ROOT_Z_MID, 1)
        apply_leg_pose("RIGHT", current, right_y, FOOT_T, 0.0, root_y, ROOT_Z_MID, 1)
        animate_upper_body(current, 0.0, stair=True)
        key_root(current, 0.0, root_y, ROOT_Z_MID, 0.0)
    frame += PAUSE_FRAMES
    STAIR_START_FRAME = frame

    left_z = FOOT_T
    right_z = FOOT_T

    def climb_step(frame, left_y, right_y, left_z, right_z, target_y, target_z):
        # Hướng +Y: chân ở sau có Y nhỏ hơn.
        swing_left = left_y < right_y
        if swing_left:
            old_y, old_z = left_y, left_z
            stance_y, stance_z = right_y, right_z
        else:
            old_y, old_z = right_y, right_z
            stance_y, stance_z = left_y, left_z

        start = frame
        end = frame + STAIR_STEP_FRAMES - 1
        assist_intervals.append((start, end, "LEFT" if swing_left else "RIGHT", "STAIR"))

        support_level = stance_z - FOOT_T
        target_level = target_z - FOOT_T

        for f in range(STAIR_STEP_FRAMES):
            u = f / max(1, STAIR_STEP_FRAMES - 1)
            s = smoothstep(u)
            current = frame + f

            sy = old_y + (target_y - old_y) * s
            sz = old_z + (target_z - old_z) * s + STAIR_CLEARANCE * math.sin(math.pi * u)

            if swing_left:
                ly, lz = sy, sz
                ry, rz = stance_y, stance_z
            else:
                ly, lz = stance_y, stance_z
                ry, rz = sy, sz

            load_phase = smoothstep((u - 0.42) / 0.58)
            level = support_level + (target_level - support_level) * load_phase
            root_z = ROOT_Z_MID + level - 0.010 * math.sin(math.pi * u)
            root_y = (ly + ry) / 2.0

            apply_leg_pose("LEFT", current, ly, lz, 0.0, root_y, root_z, 1)
            apply_leg_pose("RIGHT", current, ry, rz, 0.0, root_y, root_z, 1)
            animate_upper_body(current, 0.0, stair=True)
            key_root(current, 0.0, root_y, root_z, 0.0)

        if swing_left:
            left_y, left_z = target_y, target_z
        else:
            right_y, right_z = target_y, target_z

        return frame + STAIR_STEP_FRAMES, left_y, right_y, left_z, right_z

    # 11C) Leo từng bậc.
    for i in range(STAIR_COUNT):
        target_y = FIRST_STAIR_Y + i * STAIR_DEPTH
        target_z = FOOT_T + (i + 1) * STAIR_HEIGHT
        frame, left_y, right_y, left_z, right_z = climb_step(
            frame, left_y, right_y, left_z, right_z, target_y, target_z
        )

    # Đưa cả hai chân lên landing.
    frame, left_y, right_y, left_z, right_z = climb_step(
        frame, left_y, right_y, left_z, right_z,
        landing_y - 0.10, FOOT_T + TOP_HEIGHT
    )
    frame, left_y, right_y, left_z, right_z = climb_step(
        frame, left_y, right_y, left_z, right_z,
        landing_y + 0.10, FOOT_T + TOP_HEIGHT
    )

    # Giữ tư thế trên đỉnh.
    hold_root_y = (left_y + right_y) / 2.0
    HOLD_FRAMES = 36
    for f in range(HOLD_FRAMES):
        current = frame + f
        apply_leg_pose("LEFT", current, left_y, left_z, 0.0, hold_root_y, ROOT_Z_MID + TOP_HEIGHT, 1)
        apply_leg_pose("RIGHT", current, right_y, right_z, 0.0, hold_root_y, ROOT_Z_MID + TOP_HEIGHT, 1)
        animate_upper_body(current, 0.0, stair=True)
        key_root(current, 0.0, hold_root_y, ROOT_Z_MID + TOP_HEIGHT, 0.0)
    frame += HOLD_FRAMES

    # 11D) Contact sensors.
    def add_sensor(name):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12)
        sensor = bpy.context.object
        sensor.name = name
        sensor.scale = (0.05, 0.05, 0.018)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        sensor.data.materials.append(MAT_CONTACT_OFF)
        return sensor

    LEFT_SENSOR = add_sensor("LEFT_CONTACT_SENSOR")
    RIGHT_SENSOR = add_sensor("RIGHT_CONTACT_SENSOR")

    def classify_terrain(obj):
        if obj is None:
            return None
        name = obj.name
        if name.startswith("CLIMB_STAIR_") or name == "CLIMB_LANDING":
            return "STAIR"
        if name == "PHYSICS_RAMP":
            return "RAMP"
        if name == "ROAD":
            return "FLAT"
        return None

    def cast_to_valid_terrain(scene, sole_point, max_distance=0.25):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        direction = Vector((0.0, 0.0, -1.0))
        origin = sole_point + Vector((0.0, 0.0, 0.10))
        remaining = max_distance

        for _ in range(20):
            if remaining <= 0.0:
                break
            hit, location, normal, index, obj, matrix = scene.ray_cast(
                depsgraph, origin, direction, distance=remaining
            )
            if not hit or obj is None:
                return None

            travelled = (location - origin).length
            terrain = classify_terrain(obj)
            if terrain is not None:
                return terrain, obj, location

            # Bỏ qua bàn chân, body, sensor, text, road mark...
            origin = location + direction * 0.002
            remaining -= travelled + 0.002

        return None

    def contact_state(scene, foot):
        sample_ys = (-FOOT_LENGTH * 0.35, 0.0, FOOT_LENGTH * 0.35)
        best = None

        for local_y in sample_ys:
            sole = foot.matrix_world @ Vector((0.0, local_y, -FOOT_T / 2.0))
            result = cast_to_valid_terrain(scene, sole)
            if result is None:
                continue
            terrain, obj, location = result
            gap = sole.z - location.z
            if best is None or abs(gap) < abs(best[3]):
                best = (terrain, obj, location, gap, sole)

        if best is None:
            return False, "AIR", None, None, foot.matrix_world.translation.copy()

        terrain, obj, location, gap, sole = best
        contact = abs(gap) <= CONTACT_TOLERANCE
        return contact, terrain, obj, gap, sole

    def set_sensor_material(sensor, contact):
        sensor.data.materials.clear()
        sensor.data.materials.append(MAT_CONTACT_ON if contact else MAT_CONTACT_OFF)

    def soft_exo_contact_update(scene):
        left_contact, left_terrain, left_obj, left_gap, left_sole = contact_state(scene, LEFT_FOOT)
        right_contact, right_terrain, right_obj, right_gap, right_sole = contact_state(scene, RIGHT_FOOT)

        LEFT_SENSOR.location = left_sole + Vector((0.0, 0.0, 0.02))
        RIGHT_SENSOR.location = right_sole + Vector((0.0, 0.0, 0.02))
        set_sensor_material(LEFT_SENSOR, left_contact)
        set_sensor_material(RIGHT_SENSOR, right_contact)

        scene["LEFT_CONTACT"] = bool(left_contact)
        scene["RIGHT_CONTACT"] = bool(right_contact)
        scene["LEFT_TERRAIN"] = left_terrain
        scene["RIGHT_TERRAIN"] = right_terrain
        scene["LEFT_GAP_M"] = float(left_gap if left_gap is not None else 999.0)
        scene["RIGHT_GAP_M"] = float(right_gap if right_gap is not None else 999.0)
        scene["LEFT_HIT_OBJECT"] = left_obj.name if left_obj else "NONE"
        scene["RIGHT_HIT_OBJECT"] = right_obj.name if right_obj else "NONE"

    bpy.app.handlers.frame_change_post.append(soft_exo_contact_update)

# ============================================================
# 12) ÁP DỤNG GLOW + UI SAU KHI CÓ ĐỦ TẤT CẢ INTERVAL
# ============================================================

if STAGE >= 3:
    OFF = 0.15
    ON = 10.0

    # Khởi tạo cả hai tắt.
    glow_key(LEFT_STRENGTH, 1, OFF)
    glow_key(RIGHT_STRENGTH, 1, OFF)

    for start, end, side, mode in assist_intervals:
        fade = min(3, max(1, (end - start + 1) // 6))
        active = LEFT_STRENGTH if side == "LEFT" else RIGHT_STRENGTH
        inactive = RIGHT_STRENGTH if side == "LEFT" else LEFT_STRENGTH
        glow_key(inactive, start, OFF)
        glow_key(inactive, end, OFF)
        glow_key(active, start, OFF)
        glow_key(active, start + fade, ON)
        glow_key(active, max(start + fade, end - fade), ON)
        glow_key(active, end, OFF)

if STAGE >= 4:
    visibility_key(LEFT_TEXT, 1, False)
    visibility_key(RIGHT_TEXT, 1, False)

    for start, end, side, mode in assist_intervals:
        if side == "LEFT":
            visibility_key(LEFT_TEXT, start, True)
            visibility_key(RIGHT_TEXT, start, False)
            visibility_key(LEFT_TEXT, end, True)
        else:
            visibility_key(RIGHT_TEXT, start, True)
            visibility_key(LEFT_TEXT, start, False)
            visibility_key(RIGHT_TEXT, end, True)

# ============================================================
# 13) FINISH
# ============================================================

scene.frame_start = 1
scene.frame_end = max(1, frame - 1)
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100

# Stage 5 bắt đầu xem từ đoạn gần cầu thang; các stage khác từ frame 1.
if STAGE >= 5:
    preview_frame = max(1, STAIR_START_FRAME - PAUSE_FRAMES - STEP_FRAMES)
else:
    preview_frame = 1

scene.frame_set(preview_frame)
bpy.context.view_layer.update()

if STAGE >= 5:
    soft_exo_contact_update(scene)

recommended_names = {
    1: "01_without_assist.blend",
    2: "02_with_assist.blend",
    3: "03_with_assist_glow.blend",
    4: "04_with_assist_ui.blend",
    5: "05_physics.blend",
}

print("")
print("============================================")
print("SOFT-EXO PIPELINE READY")
print("STAGE        :", STAGE)
print("SAVE AS      :", recommended_names[STAGE])
print("CADENCE      :", CADENCE, "steps/min")
print("STEP LENGTH  :", STEP_LENGTH, "m")
print("END FRAME    :", scene.frame_end)
if STAGE >= 5:
    print("STAIR START  :", STAIR_START_FRAME)
    print("CONTACT TOL. :", CONTACT_TOLERANCE, "m")
print("============================================")
