"""
SHU Hero Video Previs - Blender build script (Blender 4.4 / bpy).

Builds the whole 15 s previs from scratch: salon set, fixed camera, client
(seated, in a cape), stylist (IK rig), three swappable hair models
(long / medium / short), props and all keyframed animation, then saves
SHU_Hero_Video_Previs.blend next to this file.

  python3 build_previs.py                      # build + save .blend
  python3 build_previs.py --stills DIR [--res 960 --samples 16] [--times 1.0,5.5]
  python3 build_previs.py --render DIR [--res 1920 --samples 24]   # PNG frames

Timeline (30 fps, frames 1-450):
  CUT1  0-3 s   Before : long dry hair, stylist touches / checks / trims ends
  CUT2  3-10 s  Cutting: jump cut to wet hair, long -> medium (4.55 s)
                -> short (6.85 s), dryer from 7.5 s
  CUT3 10-15 s  After  : jump cut to styled short hair, finishing touches,
                13-15 s final hold (hands on shoulders, client smiles)
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, Quaternion, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH = os.path.join(HERE, "SHU_Hero_Video_Previs.blend")

FPS = 30
FRAME_END = 450
CUT2_T, CUT3_T = 3.0, 10.0


def F(t):
    return int(round(1 + t * FPS))


def pre(t):
    """Last moment before a jump cut at t."""
    return t - 1.0 / FPS


CUT_LAST_FRAMES = {F(CUT2_T) - 1, F(CUT3_T) - 1}

rng = random.Random(7)

# --------------------------------------------------------------------------
# Scene
# --------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "SHU_Hero_Previs"
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = FRAME_END
scene.frame_set(1)
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 24
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.05
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.cycles.diffuse_bounces = 2
scene.cycles.glossy_bounces = 1
scene.cycles.transmission_bounces = 1
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
scene.render.use_persistent_data = True
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = 0.0
scene.render.image_settings.file_format = "PNG"

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.93, 0.9, 0.86, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.22


def coll(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


C_CAM = coll("01_Camera")
C_SET = coll("02_Salon_Set")
C_CLIENT = coll("03_Client")
C_HAIR = coll("04_Client_Hair")
C_STYL = coll("05_Stylist")
C_PROPS = coll("06_Props")
C_LIGHT = coll("07_Lights")

# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------


def mat(name, color, rough=0.5, metal=0.0, coat=0.0, sheen=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
    m.diffuse_color = (*color, 1)
    m.roughness = rough
    return m


M_WALL = mat("M_Wall_Ivory", (0.80, 0.765, 0.70), 0.92)
M_FLOOR = mat("M_Floor_Greige", (0.55, 0.50, 0.44), 0.6)
M_WOOD = mat("M_Wood_NaturalOak", (0.46, 0.31, 0.19), 0.55)
M_MIRROR = mat("M_Mirror", (0.55, 0.57, 0.6), 0.08, metal=1.0)
M_CHAIR = mat("M_Chair_Leather_Sand", (0.52, 0.42, 0.31), 0.42)
M_CHROME = mat("M_Chrome", (0.8, 0.8, 0.8), 0.18, metal=1.0)
M_CAPE = mat("M_Cape_Ivory", (0.80, 0.79, 0.76), 0.75, sheen=0.3)
M_SKIN_C = mat("M_Skin_Client", (0.86, 0.62, 0.50), 0.5)
M_SKIN_S = mat("M_Skin_Stylist", (0.72, 0.50, 0.37), 0.5)
M_EYEW = mat("M_Eye_White", (0.82, 0.8, 0.77), 0.3)
M_IRIS = mat("M_Eye_Iris", (0.025, 0.017, 0.013), 0.2)
M_BROW = mat("M_Brow", (0.07, 0.045, 0.032), 0.6)
M_LIP = mat("M_Lip", (0.55, 0.22, 0.2), 0.4)
M_SHIRT = mat("M_Stylist_Shirt_Stone", (0.30, 0.27, 0.24), 0.7)
M_PANTS = mat("M_Stylist_Pants", (0.03, 0.03, 0.032), 0.7)
M_HAIR_S = mat("M_Stylist_Hair", (0.018, 0.015, 0.013), 0.5)
M_DRYER = mat("M_Dryer_Charcoal", (0.045, 0.045, 0.048), 0.35)
M_CERAMIC = mat("M_Ceramic", (0.78, 0.74, 0.68), 0.35)
M_BOTTLE = mat("M_Bottle", (0.62, 0.54, 0.44), 0.3)
M_STEM = mat("M_Dried_Stem", (0.55, 0.45, 0.30), 0.8)


def _sock(sockets, ident):
    for s in sockets:
        if s.identifier == ident:
            return s
    raise KeyError(ident)


def hair_material():
    """Client hair. Node 'Wetness' (0 dry .. 1 wet) is keyframed."""
    m = bpy.data.materials.new("M_Hair_Client")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    wet = nt.nodes.new("ShaderNodeValue")
    wet.name = wet.label = "Wetness"
    wet.outputs[0].default_value = 0.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(wet.outputs[0], _sock(mix.inputs, "Factor_Float"))
    _sock(mix.inputs, "A_Color").default_value = (0.036, 0.020, 0.012, 1)
    _sock(mix.inputs, "B_Color").default_value = (0.013, 0.008, 0.0055, 1)
    nt.links.new(_sock(mix.outputs, "Result_Color"), b.inputs["Base Color"])
    rough = nt.nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.5
    rough.inputs["To Max"].default_value = 0.26
    nt.links.new(wet.outputs[0], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], b.inputs["Roughness"])
    coat = nt.nodes.new("ShaderNodeMapRange")
    coat.inputs["To Min"].default_value = 0.0
    coat.inputs["To Max"].default_value = 0.3
    nt.links.new(wet.outputs[0], coat.inputs["Value"])
    nt.links.new(coat.outputs["Result"], b.inputs["Coat Weight"])
    b.inputs["Coat Roughness"].default_value = 0.14
    spec = nt.nodes.new("ShaderNodeMapRange")
    spec.inputs["To Min"].default_value = 0.22
    spec.inputs["To Max"].default_value = 0.4
    nt.links.new(wet.outputs[0], spec.inputs["Value"])
    nt.links.new(spec.outputs["Result"], b.inputs["Specular IOR Level"])
    m.diffuse_color = (0.036, 0.020, 0.012, 1)
    return m, wet


M_HAIR, HAIR_WET = hair_material()

# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------


def mesh_obj(name, bm, collection, material=None, smooth=True, sharp_angle=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.shade_smooth()
    if sharp_angle is not None:
        me.set_sharp_from_angle(angle=math.radians(sharp_angle))
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    if material:
        me.materials.append(material)
    return ob


def empty(name, loc, collection, size=0.05, kind="PLAIN_AXES"):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind
    e.empty_display_size = size
    e.location = loc
    collection.objects.link(e)
    return e


def bm_ellipsoid(radii, segs=32, rings=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2]))
    return bm


def ellipsoid(name, loc, radii, collection, material, segs=32, rings=16, rot=(0, 0, 0)):
    ob = mesh_obj(name, bm_ellipsoid(radii, segs, rings), collection, material)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def bm_capsule(length, r0, r1, segs=16, rings=10):
    """Capsule from local origin along +Y."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        co = Vector((x, z, -y))
        if co.y > 1e-6:
            co = co * r1
            co.y += length
        else:
            co = co * r0
        v.co = co
    return bm


def capsule(name, p0, p1, r0, r1, collection, material, segs=16, rings=10):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    ob = mesh_obj(name, bm_capsule(d.length, r0, r1, segs, rings), collection, material)
    ob.location = p0
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("Y", "Z")
    return ob


def rbox(name, loc, size, collection, material, bevel=0.02, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=3,
                        affect="EDGES", profile=0.5)
    ob = mesh_obj(name, bm, collection, material, smooth=True, sharp_angle=40)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def bm_lathe(profile, segs=48, sx=1.0, sy=1.0, yoff=0.0, cap_bottom=False):
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        rings.append([bm.verts.new((r * math.cos(a) * sx, r * math.sin(a) * sy + yoff, z))
                      for a in [2 * math.pi * i / segs for i in range(segs)]])
    for k in range(len(rings) - 1):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    if cap_bottom:
        bm.faces.new(list(reversed(rings[0])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_torus(R, r, segs=24, tsegs=8):
    bm = bmesh.new()
    rings = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        c = Vector((math.cos(a) * R, math.sin(a) * R, 0))
        n = Vector((math.cos(a), math.sin(a), 0))
        rings.append([bm.verts.new(c + n * (r * math.cos(b)) + Vector((0, 0, r * math.sin(b))))
                      for b in [2 * math.pi * j / tsegs for j in range(tsegs)]])
    for i in range(segs):
        for j in range(tsegs):
            bm.faces.new((rings[i][j], rings[(i + 1) % segs][j],
                          rings[(i + 1) % segs][(j + 1) % tsegs], rings[i][(j + 1) % tsegs]))
    return bm


def catmull(pts, n=5):
    pts = [Vector(p) for p in pts]
    if len(pts) < 3:
        return pts
    ext = [pts[0] + (pts[0] - pts[1])] + pts + [pts[-1] + (pts[-1] - pts[-2])]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def add_tube(bm, pts, width, thick, center_fn, segs=8, root=0.55, tip=0.3):
    """Flat hair lock swept along pts; width lies along the scalp surface."""
    n = len(pts)
    L = [0.0]
    for i in range(1, n):
        L.append(L[-1] + (pts[i] - pts[i - 1]).length)
    total = max(L[-1], 1e-6)
    rings = []
    for i, p in enumerate(pts):
        s = L[i] / total
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        out = p - center_fn(p)
        N = out - out.dot(T) * T
        if N.length < 1e-6:
            N = Vector((0, -1, 0))
        N.normalize()
        B = T.cross(N)
        k = (root + (1 - root) * smoothstep(0.0, 0.14, s)) * (tip + (1 - tip) * (1 - smoothstep(0.8, 1.0, s)))
        rings.append([bm.verts.new(p + B * (width * k * math.cos(a)) + N * (thick * k * math.sin(a)))
                      for a in [2 * math.pi * j / segs for j in range(segs)]])
    for i in range(n - 1):
        for j in range(segs):
            jj = (j + 1) % segs
            bm.faces.new((rings[i][j], rings[i][jj], rings[i + 1][jj], rings[i + 1][j]))
    for ring, p in ((rings[0], pts[0]), (rings[-1], pts[-1])):
        c = bm.verts.new(p)
        for j in range(segs):
            bm.faces.new((ring[j], ring[(j + 1) % segs], c))


# --------------------------------------------------------------------------
# Salon set (simple, low detail; left of frame kept plain for web copy)
# --------------------------------------------------------------------------
BACK_Y = 2.4


def plane(name, loc, size, rot, material):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], 0))
    ob = mesh_obj(name, bm, C_SET, material, smooth=False)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


plane("Set_BackWall", (0, BACK_Y, 1.5), (9, 3), (math.radians(90), 0, 0), M_WALL)
plane("Set_Floor", (0, -0.5, 0), (9, 7), (0, 0, 0), M_FLOOR)
plane("Set_Ceiling", (0, -0.5, 2.9), (9, 7), (math.radians(180), 0, 0), M_WALL)
plane("Set_WallLeft", (-3.2, -0.5, 1.5), (7, 3), (math.radians(90), 0, math.radians(90)), M_WALL)
plane("Set_WallRight", (3.2, -0.5, 1.5), (7, 3), (math.radians(90), 0, math.radians(-90)), M_WALL)
plane("Set_WallFront", (0, -4.2, 1.5), (9, 3), (math.radians(90), 0, math.radians(180)), M_WALL)

# Styling station on the right: arched mirror + oak frame + floating console
ST_X = 1.25


def arch_shape(w, h_rect, depth, y, zb, material, name, segs=24):
    """Arched panel (rectangle + half circle) facing -Y."""
    r = w / 2
    pts = [(-r, zb), (r, zb), (r, zb + h_rect)]
    for i in range(1, segs):
        a = math.pi * i / segs
        pts.append((r * math.cos(a), zb + h_rect + r * math.sin(a)))
    pts.append((-r, zb + h_rect))
    bm = bmesh.new()
    front = [bm.verts.new((x, y, z)) for x, z in pts]
    back = [bm.verts.new((x, y + depth, z)) for x, z in pts]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[j], front[i], back[i], back[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_obj(name, bm, C_SET, material, smooth=False)
    ob.location.x = ST_X
    return ob


arch_shape(0.70, 0.78, 0.03, BACK_Y - 0.035, 0.93, M_WOOD, "Set_Mirror_Frame")
arch_shape(0.62, 0.78, 0.01, BACK_Y - 0.045, 0.97, M_MIRROR, "Set_Mirror_Glass")
rbox("Set_Console", (ST_X, BACK_Y - 0.19, 0.80), (1.05, 0.36, 0.045), C_SET, M_WOOD, 0.008)
capsule("Set_Bottle_A", (ST_X - 0.36, BACK_Y - 0.2, 0.82), (ST_X - 0.36, BACK_Y - 0.2, 0.98), 0.035, 0.03, C_SET, M_CERAMIC)
capsule("Set_Bottle_B", (ST_X - 0.26, BACK_Y - 0.18, 0.82), (ST_X - 0.26, BACK_Y - 0.18, 0.93), 0.03, 0.026, C_SET, M_BOTTLE)
vase = mesh_obj("Set_Vase", bm_lathe([(0.0, 0.0), (0.06, 0.005), (0.085, 0.06), (0.08, 0.13), (0.045, 0.2), (0.04, 0.24)], 32, cap_bottom=False), C_SET, M_CERAMIC)
vase.location = (ST_X + 0.33, BACK_Y - 0.19, 0.822)
for i, (dx, dz, tilt) in enumerate([(-0.03, 0.55, -12), (0.0, 0.62, 3), (0.035, 0.5, 15)]):
    top = Vector((ST_X + 0.33 + dx + math.sin(math.radians(tilt)) * dz, BACK_Y - 0.19, 0.822 + 0.2 + dz))
    capsule(f"Set_Stem_{i}", (ST_X + 0.33, BACK_Y - 0.19, 1.0), top, 0.004, 0.003, C_SET, M_STEM, 6, 4)
    ellipsoid(f"Set_Plume_{i}", top, (0.035, 0.035, 0.09), C_SET, M_STEM, 12, 8,
              rot=(0, math.radians(tilt), 0))


def salon_chair(prefix, loc, rotz, collection):
    parts = []
    parts.append(mesh_obj(prefix + "_Base", bm_lathe([(0.0, 0.0), (0.27, 0.0), (0.27, 0.02), (0.2, 0.04), (0.06, 0.05), (0.05, 0.4), (0.0, 0.4)], 40), collection, M_CHROME))
    parts.append(rbox(prefix + "_Seat", (0, 0.02, 0.5), (0.52, 0.5, 0.11), collection, M_CHAIR, 0.035))
    parts.append(rbox(prefix + "_Back", (0, 0.27, 0.78), (0.48, 0.09, 0.44), collection, M_CHAIR, 0.035, rot=(math.radians(-8), 0, 0)))
    for s in (-1, 1):
        parts.append(rbox(f"{prefix}_Arm{'L' if s > 0 else 'R'}", (s * 0.29, 0.0, 0.69), (0.07, 0.44, 0.05), collection, M_CHAIR, 0.02))
        parts.append(capsule(f"{prefix}_ArmPost{'L' if s > 0 else 'R'}", (s * 0.29, 0.1, 0.55), (s * 0.29, 0.1, 0.67), 0.015, 0.015, collection, M_CHROME, 10, 6))
    root = empty(prefix, (0, 0, 0), collection, 0.3)
    for p in parts:
        p.parent = root
    root.location = loc
    root.rotation_euler = (0, 0, rotz)
    return root


salon_chair("Set_StationChair", (ST_X, 1.75, 0), math.radians(180), C_SET)
salon_chair("Client_Chair", (0, 0.0, 0), 0.0, C_CLIENT)

# --------------------------------------------------------------------------
# Client (seated, cape on). Head-relative coords: origin = head centre.
# --------------------------------------------------------------------------
HEAD_Z = 1.27
HR = Vector((0.078, 0.095, 0.115))

CAPE_PROFILE = [(0.34, 0.45), (0.31, 0.55), (0.27, 0.70), (0.26, 0.85), (0.25, 0.96),
                (0.225, 1.03), (0.17, 1.075), (0.10, 1.105), (0.066, 1.14), (0.058, 1.19)]
CAPE_SY = 0.62

cape = mesh_obj("Client_Cape", bm_lathe(CAPE_PROFILE, 64, 1.0, CAPE_SY), C_CLIENT, M_CAPE)
capsule("Client_Neck", (0, 0.01, 1.10), (0, 0.01, 1.215), 0.047, 0.045, C_CLIENT, M_SKIN_C)

HEAD = empty("CLIENT_HEAD_CTRL", (0, 0, HEAD_Z), C_CLIENT, 0.18, "SPHERE")
HEAD.rotation_mode = "XYZ"


def child(ob, parent):
    ob.parent = parent
    return ob


# head with narrower jaw
bm = bm_ellipsoid(HR, 40, 24)
for v in bm.verts:
    z = v.co.z / HR.z
    if z < 0:
        k = 1 - 0.30 * (-z) ** 1.6
        v.co.x *= k
        if v.co.y > 0:
            v.co.y *= 1 - 0.25 * (-z) ** 1.5
head_mesh = child(mesh_obj("Client_Head", bm, C_CLIENT, M_SKIN_C), HEAD)
for s in (-1, 1):
    child(ellipsoid(f"Client_Ear{'L' if s > 0 else 'R'}", (s * 0.077, 0.006, -0.006), (0.011, 0.019, 0.027), C_CLIENT, M_SKIN_C, 12, 8), HEAD)
child(ellipsoid("Client_Nose", (0, -0.094, -0.018), (0.010, 0.012, 0.017), C_CLIENT, M_SKIN_C, 16, 10), HEAD)

EYES, IRISES = [], []
for s in (-1, 1):
    side = "L" if s > 0 else "R"
    g = child(empty(f"Client_Eye{side}", (s * 0.032, -0.081, 0.012), C_CLIENT, 0.02), HEAD)
    g.rotation_euler = (0, 0, math.radians(s * 18))
    child(ellipsoid(f"Client_EyeWhite{side}", (0, 0, 0), (0.0128, 0.004, 0.0068), C_CLIENT, M_EYEW, 16, 10), g)
    iris = child(ellipsoid(f"Client_Iris{side}", (0, -0.0028, -0.0004), (0.0064, 0.0024, 0.0064), C_CLIENT, M_IRIS, 16, 10), g)
    child(capsule(f"Client_Lash{side}", (-0.0145, -0.0035, 0.0045), (0.0145, -0.0035, 0.0058), 0.0016, 0.0013, C_CLIENT, M_IRIS, 8, 4), g)
    brow = capsule(f"Client_Brow{side}", (s * 0.017, -0.092, 0.036), (s * 0.049, -0.083, 0.034), 0.0028, 0.0022, C_CLIENT, M_BROW, 8, 4)
    child(brow, HEAD)
    EYES.append(g)
    IRISES.append(iris)

# mouth with shape keys: Talk (open) / Smile
bm = bm_ellipsoid((0.0165, 0.0045, 0.0036), 24, 12)
mouth = child(mesh_obj("Client_Mouth", bm, C_CLIENT, M_LIP), HEAD)
mouth.location = (0, -0.0858, -0.052)
mouth.shape_key_add(name="Basis")
sk_talk = mouth.shape_key_add(name="Talk", from_mix=False)
sk_smile = mouth.shape_key_add(name="Smile", from_mix=False)
for i, v in enumerate(mouth.data.vertices):
    x, y, z = v.co
    sk_talk.data[i].co = Vector((x * 0.9, y, z * 2.6 - 0.0012))
    xn = x / 0.0165
    sk_smile.data[i].co = Vector((x * 1.22, y + 0.001 * xn * xn, z * 0.8 + 0.0062 * xn * xn))

# --------------------------------------------------------------------------
# Hair: three swappable models (long / medium / short) built from flat locks
# --------------------------------------------------------------------------


def scalp(u, off):
    u = u.normalized()
    return Vector((u.x * (HR.x + off), u.y * (HR.y + off), u.z * (HR.z + off)))


def az_dir(phi, el):
    p, e = math.radians(phi), math.radians(el)
    return Vector((math.sin(p) * math.cos(e), -math.cos(p) * math.cos(e), math.sin(e)))


def cape_r(z):
    if z >= CAPE_PROFILE[-1][1]:
        return 0.0
    if z <= CAPE_PROFILE[0][1]:
        return CAPE_PROFILE[0][0]
    for (r0, z0), (r1, z1) in zip(CAPE_PROFILE, CAPE_PROFILE[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return 0.0


def push_out(p, front, margin):
    """Keep hair (head-relative point) outside the cape; drape front or back."""
    z = p.z + HEAD_Z
    r = cape_r(z)
    if r <= 0:
        return p
    a, b = r + margin, r * CAPE_SY + margin
    if abs(p.x) >= a or (p.x / a) ** 2 + (p.y / b) ** 2 >= 1:
        return p
    yb = b * math.sqrt(1 - (p.x / a) ** 2)
    return Vector((p.x, -yb if front else yb, p.z))


def hair_center(p):
    return Vector((0, 0.004, min(p.z, 0.0)))


STYLES = {
    # end_abs(aphi): absolute z of lock ends
    # spread: (front x at the ends for the frontmost / side locks) -> hair fans out over the shoulders
    "long": dict(off=0.007, bulge=0.003, flare=0.0, curl=0.02, width=0.04, thick=0.009,
                 spread=(0.075, 0.19), el=lambda a: 14 if a < 64 else 0,
                 end=lambda a: 1.07 if a < 64 else 0.86),
    "medium": dict(off=0.007, bulge=0.003, flare=0.0, curl=0.006, width=0.04, thick=0.009,
                   spread=(0.075, 0.16), el=lambda a: 14 if a < 64 else 0,
                   end=lambda a: 1.045 if a < 64 else 1.02),
    "short": dict(off=0.012, bulge=0.008, flare=0.0, curl=0.02, width=0.036, thick=0.010, spread=None,
                  el=lambda a: 12 if a < 64 else -4,
                  end=lambda a: 1.175 if a < 64 else (1.152 if a < 125 else 1.165)),
}


def lock_points(phi, style, layer_off, end_jitter):
    st = STYLES[style]
    side = 1 if phi >= 0 else -1
    aphi = abs(phi)
    front_root = Vector((0.03 * side, -0.60, 0.80))
    crown_root = Vector((0.03 * side, 0.40, 0.92))
    s_r = min(max((aphi - 50) / 110, 0.0), 1.0)
    root_u = front_root.normalized().slerp(crown_root.normalized(), s_r)
    S_u = az_dir(phi, st["el"](aphi))
    off = st["off"] + layer_off
    pts = []
    for k in range(7):
        t = k / 6
        u = root_u.slerp(S_u, t)
        pts.append(scalp(u, off * (0.55 + 0.45 * t) + st["bulge"] * math.sin(math.pi * t)))
    S = pts[-1]
    end_rel = st["end"](aphi) + end_jitter - HEAD_Z
    front = aphi <= 100
    margin = st["thick"] + 0.004
    n = max(2, int(math.ceil((S.z - end_rel) / 0.03)))
    if st["spread"]:
        x0, x1 = st["spread"]
        if front:
            x_end = side * (x0 + (x1 - x0) * min(max((aphi - 54) / 46, 0.0), 1.0))
        else:
            x_end = side * (x1 - (x1 - 0.02) * min(max((aphi - 100) / 80, 0.0), 1.0))
    else:
        x_end = S.x
    for k in range(1, n + 1):
        t = k / n
        z = S.z + (end_rel - S.z) * t
        # fan out once the hair reaches the shoulders (~ 0.2 m below the head centre)
        w = smoothstep(-0.08, -0.26, z)
        x = S.x + (x_end - S.x) * w
        p = Vector((x * (1 + st["flare"] * t), S.y * (1 + st["flare"] * t), z))
        pts.append(push_out(p, front, margin))
    # C-curl: ends turn inward (towards the body / jaw) and slightly up
    last = pts[-1]
    outward = Vector((last.x, last.y - 0.004, 0))
    if outward.length > 1e-6:
        outward.normalize()
    c = st["curl"]
    if style == "long" and aphi < 64:
        c = -c * 0.8  # face-framing layer flicks outward
    for f_in, f_up in ((0.55, 0.25), (1.0, 0.8)):
        q = last - outward * (c * f_in) + Vector((0, 0, abs(c) * f_up))
        pts.append(push_out(q, front, margin))
    return pts


def build_hair(name, style):
    bm = bmesh.new()
    st = STYLES[style]
    # scalp cap
    cap = bm_ellipsoid(HR + Vector((0.007, 0.007, 0.007)) + Vector((0, 0, 0.002)), 40, 24)
    kill = []
    for v in cap.verts:
        u = Vector((v.co.x / HR.x, v.co.y / HR.y, v.co.z / HR.z)).normalized()
        az = abs(math.degrees(math.atan2(u.x, -u.y)))
        keep = (az > 60 and u.z > -0.72) or u.z > 0.62
        if not keep:
            kill.append(v)
    bmesh.ops.delete(cap, geom=kill, context="VERTS")
    me_tmp = bpy.data.meshes.new("tmp")
    cap.to_mesh(me_tmp)
    cap.free()
    bm.from_mesh(me_tmp)
    bpy.data.meshes.remove(me_tmp)
    # locks, two layers
    for layer, (step0, lo, jit) in enumerate(((0.0, 0.0, 0.0), (3.0, 0.005, 0.012))):
        phi = 56 + step0
        while phi <= 180:
            for side in (1, -1):
                if phi >= 179.9 and side < 0:
                    continue
                ej = rng.uniform(-0.012, 0.012) + jit
                pts = catmull(lock_points(side * phi, style, lo, ej), 4)
                add_tube(bm, pts, st["width"], st["thick"], hair_center)
            phi += 6.0
    # see-through bangs
    for i in range(9):
        x = -0.044 + i * 0.011
        xn = x / HR.x
        bpts = []
        for k in range(6):
            el = 58 - k * 7.4
            e = math.radians(el)
            u = Vector((xn * math.cos(e), -math.sqrt(max(1 - xn * xn, 0.0)) * math.cos(e), math.sin(e)))
            bpts.append(scalp(u, 0.006 - 0.003 * k / 5))
        tip = bpts[-1] + Vector((0, 0.004, -0.004))
        bpts.append(tip)
        add_tube(bm, catmull(bpts, 4), 0.0075, 0.0028, hair_center, 6, 0.8, 0.25)
    ob = mesh_obj(name, bm, C_HAIR, M_HAIR)
    ob.parent = HEAD
    return ob


HAIR_LONG = build_hair("hair_long", "long")
HAIR_MED = build_hair("hair_medium", "medium")
HAIR_SHORT = build_hair("hair_short", "short")

# lifted hair section (stretches from scalp to the stylist's fingers)
bm = bmesh.new()
add_tube(bm, [Vector((0, t, 0)) for t in [0, 0.25, 0.5, 0.75, 1.0]], 0.016, 0.006,
         lambda p: p - Vector((0, 0, 1)), 8, 0.9, 0.5)
SECTION = mesh_obj("hair_section_lifted", bm, C_HAIR, M_HAIR)
SECTION.parent = HEAD

# --------------------------------------------------------------------------
# Stylist rig (IK arms, hands driven by empties in world space)
# --------------------------------------------------------------------------
arm_data = bpy.data.armatures.new("stylist_rig")
arm_data.display_type = "STICK"
RIG = bpy.data.objects.new("STYLIST_RIG", arm_data)
C_STYL.objects.link(RIG)
bpy.context.view_layer.objects.active = RIG
RIG.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_data.edit_bones


def bone(name, h, t, parent=None, connect=False):
    b = eb.new(name)
    b.head, b.tail, b.roll = h, t, 0.0
    if parent:
        b.parent = eb[parent]
        b.use_connect = connect


SH_Z = 1.42
bone("hips", (0, 0, 0.92), (0, 0, 1.08))
bone("spine", (0, 0, 1.08), (0, 0, 1.28), "hips", True)
bone("chest", (0, 0, 1.28), (0, 0, 1.45), "spine", True)
bone("neck", (0, 0, 1.45), (0, 0, 1.52), "chest", True)
bone("head", (0, 0, 1.52), (0, 0, 1.72), "neck", True)
for s, side in ((-1, "R"), (1, "L")):
    bone(f"upper_arm.{side}", (s * 0.18, 0.0, SH_Z), (s * 0.20, 0.035, 1.135), "chest")
    bone(f"forearm.{side}", (s * 0.20, 0.035, 1.135), (s * 0.20, -0.02, 0.875), f"upper_arm.{side}", True)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()


def parent_bone(ob, bname):
    bpy.context.view_layer.update()
    mw = ob.matrix_world.copy()
    ob.parent = RIG
    ob.parent_type = "BONE"
    ob.parent_bone = bname
    bpy.context.view_layer.update()
    ob.matrix_world = mw
    return ob


# body meshes (rest pose: at origin, facing -Y)
parent_bone(ellipsoid("Stylist_Pelvis", (0, 0, 0.98), (0.16, 0.1, 0.11), C_STYL, M_PANTS), "hips")
for s, side in ((-1, "R"), (1, "L")):
    parent_bone(capsule(f"Stylist_Leg.{side}", (s * 0.085, 0, 0.93), (s * 0.09, 0, 0.07), 0.068, 0.048, C_STYL, M_PANTS), "hips")
    parent_bone(ellipsoid(f"Stylist_Shoe.{side}", (s * 0.09, -0.04, 0.035), (0.045, 0.12, 0.035), C_STYL, M_PANTS, 16, 8), "hips")
parent_bone(ellipsoid("Stylist_Abdomen", (0, 0.008, 1.14), (0.14, 0.085, 0.15), C_STYL, M_SHIRT), "spine")
parent_bone(ellipsoid("Stylist_Chest", (0, 0, 1.33), (0.175, 0.11, 0.14), C_STYL, M_SHIRT), "chest")
parent_bone(capsule("Stylist_Shoulders", (-0.17, 0, 1.405), (0.17, 0, 1.405), 0.055, 0.055, C_STYL, M_SHIRT), "chest")
parent_bone(capsule("Stylist_Neck", (0, 0.0, 1.43), (0, 0.0, 1.535), 0.045, 0.042, C_STYL, M_SKIN_S), "neck")
parent_bone(ellipsoid("Stylist_Head", (0, 0, 1.60), (0.078, 0.093, 0.108), C_STYL, M_SKIN_S), "head")
bm = bm_ellipsoid((0.086, 0.101, 0.098), 32, 16)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not (v.co.z > 0.035 or (v.co.y > 0.03 and v.co.z > -0.07))], context="VERTS")
sh = mesh_obj("Stylist_Hair", bm, C_STYL, M_HAIR_S)
sh.location = (0, 0.008, 1.625)
parent_bone(sh, "head")
for s, side in ((-1, "R"), (1, "L")):
    parent_bone(ellipsoid(f"Stylist_Eye.{side}", (s * 0.03, -0.083, 1.607), (0.009, 0.004, 0.006), C_STYL, M_IRIS, 12, 8), "head")
    parent_bone(capsule(f"Stylist_Brow.{side}", (s * 0.015, -0.088, 1.632), (s * 0.045, -0.08, 1.63), 0.0035, 0.003, C_STYL, M_HAIR_S, 8, 4), "head")
    parent_bone(capsule(f"Stylist_UpperArm.{side}", (s * 0.18, 0.0, SH_Z), (s * 0.20, 0.035, 1.135), 0.047, 0.04, C_STYL, M_SHIRT), f"upper_arm.{side}")
    parent_bone(capsule(f"Stylist_Forearm.{side}", (s * 0.20, 0.035, 1.135), (s * 0.20, -0.02, 0.875), 0.036, 0.028, C_STYL, M_SKIN_S), f"forearm.{side}")

# hand targets (wrist position, +Y = finger direction, -Z = palm)
IK = {}
GRIP = {}
for s, side in ((-1, "R"), (1, "L")):
    t = empty(f"IK_hand.{side}", (s * 0.2, -0.02, 0.875), C_STYL, 0.06, "ARROWS")
    t.rotation_mode = "QUATERNION"
    IK[side] = t
    g = empty(f"grip.{side}", (0, 0.078, -0.004), C_STYL, 0.02)
    g.parent = t
    GRIP[side] = g
    hand = ellipsoid(f"Stylist_Hand.{side}", (0, 0.047, 0), (0.028, 0.052, 0.0135), C_STYL, M_SKIN_S, 16, 10)
    hand.parent = t
    th = capsule(f"Stylist_Thumb.{side}", (s * -0.02, 0.012, -0.006), (s * -0.036, 0.048, -0.012), 0.0095, 0.008, C_STYL, M_SKIN_S, 8, 6)
    th.parent = t
    pole = empty(f"pole_elbow.{side}", (s * 0.6, 0.45, 0.85), C_STYL, 0.04)
    pole.parent = RIG
    c = RIG.pose.bones[f"forearm.{side}"].constraints.new("IK")
    c.target = t
    c.pole_target = pole
    c.chain_count = 2
    c.use_stretch = True
    RIG.pose.bones[f"forearm.{side}"].ik_stretch = 0.08
    RIG.pose.bones[f"upper_arm.{side}"].ik_stretch = 0.08

for pb in RIG.pose.bones:
    pb.rotation_mode = "XYZ"

LOOK = empty("stylist_look_target", (0, 0, 1.3), C_STYL, 0.05, "SPHERE")
dt = RIG.pose.bones["head"].constraints.new("DAMPED_TRACK")
dt.target = LOOK
dt.track_axis = "TRACK_Z"
dt.influence = 0.75


def pick_pole_angles():
    """Choose the pole angle that makes each elbow point towards its pole."""
    dg = bpy.context.evaluated_depsgraph_get()
    for s, side in ((-1, "R"), (1, "L")):
        IK[side].location = (s * 0.1, -0.35, 1.3)
        c = RIG.pose.bones[f"forearm.{side}"].constraints["IK"]
        best = None
        for ang in (-90, 0, 90, 180):
            c.pole_angle = math.radians(ang)
            bpy.context.view_layer.update()
            pe = RIG.evaluated_get(dg).pose.bones[f"forearm.{side}"]
            elbow = RIG.matrix_world @ pe.head
            shoulder = Vector((s * 0.18, 0.0, SH_Z))
            wrist = IK[side].location
            axis = (wrist - shoulder).normalized()
            pole_dir = Vector((s * 0.6, 0.45, 0.85)) - shoulder
            pole_dir = (pole_dir - pole_dir.dot(axis) * axis).normalized()
            eo = elbow - shoulder
            eo = (eo - eo.dot(axis) * axis)
            score = eo.normalized().dot(pole_dir) if eo.length > 1e-5 else -1
            if best is None or score > best[0]:
                best = (score, ang)
        c.pole_angle = math.radians(best[1])
        print(f"pole angle {side}: {best[1]} (score {best[0]:.2f})")
        IK[side].location = (s * 0.2, -0.02, 0.875)


pick_pole_angles()

# --------------------------------------------------------------------------
# Props: scissors (right hand) and dryer (right hand)
# --------------------------------------------------------------------------
SCISSORS = empty("Prop_Scissors", (0, 0.0, -0.006), C_PROPS, 0.03)
SCISSORS.parent = GRIP["R"]
BLADES = []
for s in (-1, 1):
    piv = empty(f"Prop_Scissors_Blade{'A' if s > 0 else 'B'}", (0, 0, s * 0.0015), C_PROPS, 0.01)
    piv.parent = SCISSORS
    bl = capsule(f"Prop_Scissors_BladeMesh{'A' if s > 0 else 'B'}", (0, -0.01, 0), (0, 0.095, 0), 0.0055, 0.0012, C_PROPS, M_CHROME, 8, 4)
    bl.scale = (1, 1, 0.35)
    bl.parent = piv
    ring = mesh_obj(f"Prop_Scissors_Ring{'A' if s > 0 else 'B'}", bm_torus(0.011, 0.0025, 16, 6), C_PROPS, M_CHROME)
    ring.location = (s * 0.012, -0.035, 0)
    ring.parent = piv
    capsule(f"Prop_Scissors_Shank{'A' if s > 0 else 'B'}", (0, 0, 0), (s * 0.008, -0.026, 0), 0.0025, 0.0025, C_PROPS, M_CHROME, 6, 4).parent = piv
    piv.rotation_euler = (0, 0, math.radians(-s * 7))
    BLADES.append((piv, s))

DRYER = empty("Prop_Dryer", (0, 0.03, 0.0), C_PROPS, 0.05)
DRYER.parent = IK["R"]
for ob in (
    capsule("Prop_Dryer_Body", (0, -0.085, 0.088), (0, 0.075, 0.088), 0.038, 0.036, C_PROPS, M_DRYER, 20, 10),
    capsule("Prop_Dryer_Nozzle", (0, 0.07, 0.088), (0, 0.125, 0.088), 0.03, 0.022, C_PROPS, M_DRYER, 16, 8),
    capsule("Prop_Dryer_Handle", (0, 0.02, -0.035), (0, -0.005, 0.07), 0.018, 0.02, C_PROPS, M_DRYER, 12, 8),
):
    ob.parent = DRYER

# --------------------------------------------------------------------------
# Camera (single, fixed) and lights
# --------------------------------------------------------------------------
cam_data = bpy.data.cameras.new("CAM_Hero")
cam_data.lens = 63
cam_data.sensor_width = 36
cam_data.clip_start = 0.1
cam_data.dof.use_dof = True
cam_data.dof.aperture_fstop = 4.0
CAM = bpy.data.objects.new("CAM_Hero_Fixed", cam_data)
C_CAM.objects.link(CAM)
CAM.location = (-0.44, -3.25, 1.31)
CAM_AIM = Vector((-0.115, 0.0, 1.285))
CAM.rotation_euler = (CAM_AIM - CAM.location).to_track_quat("-Z", "Y").to_euler()
cam_data.dof.focus_distance = (Vector((0, -0.05, 1.27)) - CAM.location).length
scene.camera = CAM


def area_light(name, loc, target, energy, size, color=(1, 1, 1), size_y=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = color
    ld.shape = "RECTANGLE"
    ld.size = size
    ld.size_y = size_y or size
    lo = bpy.data.objects.new(name, ld)
    C_LIGHT.objects.link(lo)
    lo.location = loc
    lo.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return lo


area_light("Light_Key_Window", (-2.6, -1.9, 2.3), (0, 0.2, 1.25), 330, 2.6, (1.0, 0.96, 0.9), 1.8)
area_light("Light_Fill", (2.4, -2.6, 1.7), (0, 0, 1.2), 90, 2.0, (1.0, 0.98, 0.95))
area_light("Light_Top_Soft", (0, -0.3, 2.85), (0, -0.3, 0), 90, 3.0, (1.0, 0.97, 0.93))
area_light("Light_Rim", (1.6, 1.9, 2.1), (0, 0, 1.3), 70, 1.2, (0.96, 0.97, 1.0))
area_light("Light_BackWall_Wash", (0, 0.4, 2.8), (0, BACK_Y, 1.4), 60, 3.5, (1.0, 0.97, 0.92), 0.8)

# ==========================================================================
# ANIMATION
# ==========================================================================


def key(ob, path, t, value=None, index=-1):
    if value is not None:
        setattr(ob, path, value)
    ob.keyframe_insert(path, frame=F(t), index=index)


def key_visible(ob, t, visible):
    ob.hide_render = not visible
    ob.hide_viewport = not visible
    ob.keyframe_insert("hide_render", frame=F(t))
    ob.keyframe_insert("hide_viewport", frame=F(t))


def visible_ranges(obs, ranges):
    """ranges: list of (t_on, t_off). Hidden outside."""
    if not isinstance(obs, (list, tuple)):
        obs = [obs]
    for ob in obs:
        key_visible(ob, 0, False)
        for t_on, t_off in ranges:
            key_visible(ob, t_on, True)
            if t_off is not None:
                key_visible(ob, t_off, False)
    for ob in obs:
        for c in ob.children_recursive:
            if c.type == "MESH":
                key_visible(c, 0, False)
                for t_on, t_off in ranges:
                    key_visible(c, t_on, True)
                    if t_off is not None:
                        key_visible(c, t_off, False)


# ---------------- hair model switching ----------------
SWITCH_MED = 4.55
SWITCH_SHORT = 6.85
visible_ranges(HAIR_LONG, [(0, SWITCH_MED)])
visible_ranges(HAIR_MED, [(SWITCH_MED, SWITCH_SHORT)])
visible_ranges(HAIR_SHORT, [(SWITCH_SHORT, None)])

# wetness: dry -> (jump cut) wet -> drying with the dryer -> (jump cut) dry
wet_sock = HAIR_WET.outputs[0]
for t, v in ((0, 0.0), (pre(CUT2_T), 0.0), (CUT2_T, 1.0), (7.7, 1.0), (9.95, 0.25), (CUT3_T, 0.0)):
    wet_sock.default_value = v
    wet_sock.keyframe_insert("default_value", frame=F(t))

# short hair: flatter while wet, full volume once styled
HAIR_SHORT.scale = (0.955, 0.955, 0.985)
key(HAIR_SHORT, "scale", SWITCH_SHORT)
key(HAIR_SHORT, "scale", 7.7)
# dryer "wind": small sways of the hair mass
sway = [(7.9, (1.5, 0, -2.5)), (8.25, (-1.0, 0, 2.2)), (8.6, (1.8, 0, -1.8)), (8.95, (-1.2, 0, 2.6)),
        (9.3, (1.4, 0, -2.0)), (9.65, (-0.8, 0, 1.4)), (9.95, (0.0, 0, 0.0))]
key(HAIR_SHORT, "rotation_euler", 7.7, (0, 0, 0))
for i, (t, (rx, ry, rz)) in enumerate(sway):
    key(HAIR_SHORT, "rotation_euler", t, tuple(math.radians(a) for a in (rx, ry, rz)))
    sc = 0.965 + 0.012 * (i % 2) + 0.004 * i
    key(HAIR_SHORT, "scale", t, (sc, sc, 0.99))
key(HAIR_SHORT, "scale", pre(CUT3_T), (0.99, 0.99, 0.995))
key(HAIR_SHORT, "scale", CUT3_T, (1.0, 1.0, 1.0))
key(HAIR_SHORT, "rotation_euler", CUT3_T, (0, 0, 0))

# ---------------- client face and head ----------------
HEAD_BASE_ROT = (0.0, 0.0, math.radians(-2.0))  # face turned a hair towards camera


def head_rot(t, rx=0.0, ry=0.0, rz=0.0):
    key(HEAD, "rotation_euler", t, (HEAD_BASE_ROT[0] + math.radians(rx), HEAD_BASE_ROT[1] + math.radians(ry),
                                    HEAD_BASE_ROT[2] + math.radians(rz)))


for t, r in ((0, (0, 0, 0)), (0.6, (-0.8, 0.3, 0)), (1.2, (0.4, -0.3, 0.6)), (1.9, (0, 0, 1.2)),
             (2.5, (0, 0, 0.2)), (pre(CUT2_T), (0, 0, 0)), (CUT2_T, (0.6, 0, 0)), (6.0, (1.2, 0, 0)),
             (7.6, (0.6, 0, 0)), (pre(CUT3_T), (0, 0, 0)), (CUT3_T, (0, 0, 0)), (10.6, (-0.8, 0.4, 0)),
             (11.3, (0.3, -0.3, 0)), (11.9, (1.0, 0.5, -3.0)), (12.5, (0.8, 0.3, -2.4)),
             (13.1, (0, 0, 0)), (13.8, (-0.6, 0, 0)), (15.0, (-0.6, 0, 0))):
    head_rot(t, *r)

# blinks (none after 13 s so the final hold is clean)
for eye in EYES:
    key(eye, "scale", 0, (1, 1, 1))
for tb in (0.85, 2.35, 3.9, 5.95, 8.45, 10.9, 12.35):
    for eye in EYES:
        key(eye, "scale", tb, (1, 1, 1))
        key(eye, "scale", tb + 0.07, (1, 1, 0.12))
        key(eye, "scale", tb + 0.11, (1, 1, 0.12))
        key(eye, "scale", tb + 0.21, (1, 1, 1))

# gaze (iris offsets, eye-local x)
for iris in IRISES:
    base = iris.location.copy()
    for t, dx, dz in ((0, 0, 0), (1.75, 0, 0), (1.95, -0.0028, -0.0006), (2.5, -0.0028, -0.0006),
                      (2.7, 0, 0), (7.6, 0, 0), (7.8, 0.0, -0.0012), (9.8, 0.0, -0.0012),
                      (pre(CUT3_T), 0, 0), (CUT3_T, 0, 0), (11.8, 0, 0), (12.0, 0.003, -0.0008),
                      (12.55, 0.003, -0.0008), (12.8, 0, 0), (15, 0, 0)):
        key(iris, "location", t, (base.x + dx, base.y, base.z + dz))


def talk(t0, t1, amp=0.8):
    t = t0
    key(sk_talk, "value", t0 - 0.05, 0.0)
    i = 0
    while t < t1:
        v = amp * (0.35 + 0.65 * rng.random()) if i % 2 == 0 else amp * 0.1 * rng.random()
        key(sk_talk, "value", t, v)
        t += rng.uniform(0.13, 0.2)
        i += 1
    key(sk_talk, "value", t1 + 0.1, 0.0)


talk(0.25, 1.65, 0.75)
talk(10.25, 11.55, 0.7)
talk(5.3, 5.75, 0.4)
for t, v in ((0, 0.18), (1.7, 0.18), (2.2, 0.3), (pre(CUT2_T), 0.3), (CUT2_T, 0.05), (pre(CUT3_T), 0.05),
             (CUT3_T, 0.2), (12.85, 0.25), (13.55, 1.0), (15.0, 1.0)):
    key(sk_smile, "value", t, v)

# subtle breathing of the cape (client body stays still)
for i in range(9):
    t = i * 1.9
    key(cape, "scale", t, (1.0, 1.0 + 0.004 * (i % 2), 1.0 + 0.003 * (i % 2)))

# ---------------- stylist ----------------


def hand_quat(fdir, palm):
    y = Vector(fdir).normalized()
    z = -Vector(palm)
    z = (z - z.dot(y) * y).normalized()
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed()
    return m.to_quaternion()


HAND_LEN = 0.078


def hand_pose(tip, fdir, palm):
    q = hand_quat(fdir, palm)
    wrist = Vector(tip) - Vector(fdir).normalized() * HAND_LEN
    return wrist, q


_last_q = {}


def key_hand(side, t, tip, fdir, palm):
    wrist, q = hand_pose(tip, fdir, palm)
    prev = _last_q.get(side)
    if prev is not None and prev.dot(q) < 0:
        q = -q
    _last_q[side] = q
    t_ob = IK[side]
    t_ob.location = wrist
    t_ob.rotation_quaternion = q
    t_ob.keyframe_insert("location", frame=F(t))
    t_ob.keyframe_insert("rotation_quaternion", frame=F(t))


def key_body(t, x, y, rotz, lean=0.0, twist=0.0):
    RIG.location = (x, y, 0)
    RIG.rotation_euler = (0, 0, math.radians(rotz))
    RIG.keyframe_insert("location", frame=F(t))
    RIG.keyframe_insert("rotation_euler", frame=F(t))
    sp, ch = RIG.pose.bones["spine"], RIG.pose.bones["chest"]
    sp.rotation_euler = (math.radians(lean * 0.55), 0, 0)
    ch.rotation_euler = (math.radians(lean * 0.45), math.radians(twist), 0)
    sp.keyframe_insert("rotation_euler", frame=F(t))
    ch.keyframe_insert("rotation_euler", frame=F(t))


def key_look(t, p):
    LOOK.location = p
    LOOK.keyframe_insert("location", frame=F(t))


def snip(t, dur_open=0.12):
    for piv, s in BLADES:
        key(piv, "rotation_euler", t - dur_open - 0.05, (0, 0, math.radians(-s * 2)))
        key(piv, "rotation_euler", t - 0.06, (0, 0, math.radians(-s * 11)))
        key(piv, "rotation_euler", t, (0, 0, math.radians(-s * 0.5)))


# helper directions
DOWN = (0, 0, -1)
UP = (0, 0, 1)

# ---- body path ----
BODY = [
    # t,    x,     y,    rotz, lean, twist
    (0.0, 0.22, 0.38, -18, 8, 0),
    (0.9, 0.23, 0.37, -20, 9, 0),
    (1.35, 0.27, 0.29, -30, 16, -4),
    (2.4, 0.27, 0.28, -32, 19, -6),
    (pre(CUT2_T), 0.27, 0.28, -32, 19, -6),
    (CUT2_T, 0.10, 0.40, -10, 7, 0),
    (3.9, 0.08, 0.39, -8, 8, 0),
    (4.3, 0.00, 0.37, 2, 10, 4),
    (4.7, 0.02, 0.37, 0, 10, 2),
    (5.25, 0.25, 0.30, -30, 9, -2),
    (5.65, 0.26, 0.30, -30, 9, -2),
    (6.05, 0.03, 0.42, -2, 15, 0),
    (6.85, 0.03, 0.42, -2, 15, 0),
    (7.3, 0.10, 0.41, -8, 7, 0),
    (7.7, 0.12, 0.41, -10, 6, 0),
    (9.95, 0.12, 0.41, -10, 6, 0),
    (pre(CUT3_T), 0.12, 0.41, -10, 6, 0),
    (CUT3_T, 0.25, 0.35, -24, 7, 0),
    (11.0, 0.25, 0.35, -24, 7, 0),
    (11.8, 0.24, 0.36, -22, 5, 0),
    (12.8, 0.22, 0.37, -20, 7, 0),
    (13.4, 0.22, 0.38, -18, 4, 0),
    (13.95, 0.22, 0.39, -18, 1.5, 0),
    (15.0, 0.22, 0.39, -18, 1.5, 0),
]
for b in BODY:
    key_body(*b)

# ---- look target ----
for t, p in (
    (0.0, (0.0, 0.0, 1.33)), (0.9, (0.0, -0.02, 1.15)), (1.4, (0.14, -0.12, 0.98)),
    (2.6, (0.14, -0.12, 0.98)), (pre(CUT2_T), (0.14, -0.12, 0.98)),
    (CUT2_T, (0.14, -0.02, 1.48)), (4.2, (0.08, -0.02, 1.44)), (4.4, (-0.1, -0.02, 1.08)),
    (4.9, (-0.1, -0.02, 1.1)), (5.3, (0.16, -0.05, 1.3)), (5.8, (0.16, -0.05, 1.3)),
    (6.1, (0.06, 0.1, 1.42)), (6.9, (0.06, 0.1, 1.42)), (7.5, (-0.04, 0.0, 1.35)),
    (9.9, (0.0, 0.0, 1.33)), (pre(CUT3_T), (0.0, 0.0, 1.33)), (CUT3_T, (0.08, -0.03, 1.2)),
    (11.0, (0.06, -0.02, 1.2)), (11.3, (0.24, 0.05, 1.37)), (11.8, (0.0, 0.0, 1.38)),
    (12.8, (0.02, -0.05, 1.25)), (13.4, (0.06, -0.08, 1.28)), (13.9, (-0.25, -3.0, 1.28)),
    (15.0, (-0.25, -3.0, 1.28)),
):
    key_look(t, p)

# ---- right hand (scissors / dryer hand, screen-left arm) ----
R = [
    # CUT1: smooth hair down, rest, then trim ends in front of left shoulder
    (0.0, (-0.06, 0.03, 1.385), (-0.35, -0.15, -0.92), (0.4, 0.1, -0.2)),
    (0.45, (-0.095, 0.0, 1.29), (-0.2, -0.2, -0.95), (0.8, 0.1, 0.1)),
    (0.95, (-0.118, -0.03, 1.13), (-0.05, -0.2, -0.98), (0.9, 0.2, 0.0)),
    (1.35, (-0.05, 0.08, 1.17), (0.0, -0.3, -0.95), (0.3, -0.9, 0.0)),
    (1.85, (0.04, -0.05, 1.08), (0.4, -0.7, -0.4), (0.0, 0.3, -0.9)),
    (2.2, (0.12, -0.155, 0.97), (0.35, -0.55, -0.6), (0.2, 0.5, -0.8)),
    (2.45, (0.125, -0.158, 0.965), (0.35, -0.55, -0.6), (0.2, 0.5, -0.8)),
    (2.75, (0.13, -0.16, 0.955), (0.35, -0.55, -0.6), (0.2, 0.5, -0.8)),
    (pre(CUT2_T), (0.13, -0.16, 0.955), (0.35, -0.55, -0.6), (0.2, 0.5, -0.8)),
    # CUT2: cut lifted top section, then side cut line (switch to medium)
    (CUT2_T, (0.06, -0.06, 1.47), (0.5, -0.1, 0.4), (0.0, 0.2, -1.0)),
    (3.8, (0.08, -0.06, 1.49), (0.5, -0.1, 0.4), (0.0, 0.2, -1.0)),
    (4.1, (0.1, -0.06, 1.51), (0.5, -0.1, 0.4), (0.0, 0.2, -1.0)),
    (4.3, (-0.12, 0.02, 1.13), (0.1, -0.95, 0.0), (0.0, 0.0, -1.0)),
    (4.55, (-0.12, -0.02, 1.1), (0.1, -0.95, 0.0), (0.0, 0.0, -1.0)),
    (4.85, (-0.08, 0.06, 1.2), (0.3, -0.6, -0.4), (0.5, 0.0, -0.8)),
    # side point-cut on screen-right side
    (5.2, (0.16, -0.08, 1.28), (0.1, -0.2, 0.97), (-0.9, 0.0, 0.1)),
    (5.45, (0.165, -0.08, 1.25), (0.1, -0.2, 0.97), (-0.9, 0.0, 0.1)),
    (5.65, (0.12, 0.0, 1.35), (0.0, -0.5, 0.8), (-0.6, 0.2, 0.0)),
    # back of head: cut across the lifted back section
    (6.05, (0.02, 0.1, 1.4), (0.95, 0.2, 0.2), (0.0, 0.0, -1.0)),
    (6.4, (0.04, 0.11, 1.415), (0.95, 0.2, 0.2), (0.0, 0.0, -1.0)),
    (6.8, (0.06, 0.12, 1.43), (0.95, 0.2, 0.2), (0.0, 0.0, -1.0)),
    # swap scissors for the dryer (hand dips behind the client)
    (7.1, (-0.2, 0.28, 1.02), (0.0, -0.3, -0.95), (0.3, 0.0, 0.0)),
    (7.25, (-0.2, 0.28, 1.02), (0.0, -0.3, -0.95), (0.3, 0.0, 0.0)),
    # dryer: blow the top and left side, sweeping
    (7.7, (-0.2, 0.02, 1.47), (0.8, -0.1, -0.55), (0.0, 0.0, -1.0)),
    (8.1, (-0.19, -0.02, 1.43), (0.85, 0.0, -0.45), (0.0, 0.0, -1.0)),
    (8.5, (-0.18, 0.06, 1.5), (0.7, -0.2, -0.65), (0.0, 0.0, -1.0)),
    (8.9, (-0.2, 0.0, 1.42), (0.9, -0.05, -0.35), (0.0, 0.0, -1.0)),
    (9.3, (-0.17, 0.05, 1.49), (0.75, -0.15, -0.6), (0.0, 0.0, -1.0)),
    (9.7, (-0.2, 0.01, 1.44), (0.85, -0.05, -0.45), (0.0, 0.0, -1.0)),
    (pre(CUT3_T), (-0.2, 0.01, 1.44), (0.85, -0.05, -0.45), (0.0, 0.0, -1.0)),
    # CUT3: finish ends at screen-left, product, finger-comb, shoulder
    (CUT3_T, (-0.09, 0.0, 1.2), (-0.1, -0.3, -0.95), (0.9, 0.1, 0.0)),
    (10.45, (-0.095, -0.01, 1.175), (-0.1, -0.3, -0.95), (0.9, 0.1, 0.0)),
    (10.9, (-0.09, 0.0, 1.2), (-0.1, -0.3, -0.95), (0.9, 0.1, 0.0)),
    (11.25, (0.2, 0.06, 1.37), (0.7, -0.6, 0.1), (0.2, 0.0, -0.95)),
    (11.45, (0.22, 0.05, 1.38), (0.7, -0.6, 0.1), (0.2, 0.0, -0.95)),
    (11.65, (0.2, 0.06, 1.37), (0.7, -0.6, 0.1), (0.2, 0.0, -0.95)),
    (11.85, (-0.035, 0.03, 1.405), (-0.3, -0.2, -0.9), (0.5, 0.0, -0.8)),
    (12.35, (-0.1, 0.0, 1.25), (-0.1, -0.2, -0.97), (0.9, 0.2, 0.0)),
    (12.75, (-0.105, 0.0, 1.2), (-0.05, -0.2, -0.97), (0.9, 0.2, 0.0)),
    (13.35, (-0.15, 0.03, 1.075), (-0.2, -0.9, -0.3), (0.0, 0.0, -1.0)),
    (14.0, (-0.15, 0.03, 1.072), (-0.2, -0.9, -0.3), (0.0, 0.0, -1.0)),
    (15.0, (-0.15, 0.03, 1.072), (-0.2, -0.9, -0.3), (0.0, 0.0, -1.0)),
]
# ---- left hand (holding / lifting hand, screen-right arm) ----
L = [
    (0.0, (0.07, 0.03, 1.37), (0.35, -0.15, -0.92), (-0.4, 0.1, -0.2)),
    (0.45, (0.1, 0.0, 1.28), (0.2, -0.2, -0.95), (-0.8, 0.1, 0.1)),
    (0.95, (0.125, -0.04, 1.11), (0.05, -0.25, -0.97), (-0.9, 0.2, 0.0)),
    (1.35, (0.15, -0.13, 0.975), (-0.35, -0.55, 0.25), (0.0, 0.3, 1.0)),
    (1.9, (0.16, -0.14, 1.005), (-0.35, -0.55, 0.25), (0.0, 0.3, 1.0)),
    (2.2, (0.155, -0.14, 0.995), (-0.35, -0.55, 0.25), (0.0, 0.3, 1.0)),
    (pre(CUT2_T), (0.155, -0.14, 0.995), (-0.35, -0.55, 0.25), (0.0, 0.3, 1.0)),
    # CUT2: lift top section, then steady the head
    (CUT2_T, (0.15, -0.02, 1.47), (0.1, -0.3, 0.95), (-0.9, 0.0, 0.0)),
    (3.45, (0.19, -0.02, 1.57), (0.1, -0.3, 0.95), (-0.9, 0.0, 0.0)),
    (4.1, (0.19, -0.02, 1.57), (0.1, -0.3, 0.95), (-0.9, 0.0, 0.0)),
    (4.3, (-0.025, 0.02, 1.405), (-0.9, 0.05, -0.3), (0.0, 0.0, -1.0)),
    (4.8, (-0.025, 0.02, 1.405), (-0.9, 0.05, -0.3), (0.0, 0.0, -1.0)),
    (5.15, (0.21, -0.07, 1.31), (0.3, -0.8, 0.2), (-0.3, 0.0, -0.9)),
    (5.55, (0.21, -0.07, 1.31), (0.3, -0.8, 0.2), (-0.3, 0.0, -0.9)),
    (6.0, (0.13, 0.14, 1.47), (0.45, 0.1, 0.88), (-0.9, 0.2, 0.3)),
    (6.8, (0.13, 0.14, 1.47), (0.45, 0.1, 0.88), (-0.9, 0.2, 0.3)),
    (7.15, (-0.02, 0.02, 1.405), (-0.9, 0.05, -0.3), (0.0, 0.0, -1.0)),
    # drying: fingers work through the top / right side, lift a small section
    (7.7, (0.0, 0.01, 1.405), (-0.8, -0.2, -0.4), (0.0, 0.0, -1.0)),
    (8.1, (0.1, -0.01, 1.33), (0.0, -0.3, -0.95), (-0.9, 0.2, 0.0)),
    (8.5, (0.13, -0.01, 1.46), (0.2, -0.3, 0.9), (-0.9, 0.0, 0.0)),
    (8.9, (0.14, 0.0, 1.48), (0.2, -0.3, 0.9), (-0.9, 0.0, 0.0)),
    (9.3, (0.12, -0.01, 1.45), (0.2, -0.3, 0.9), (-0.9, 0.0, 0.0)),
    (9.6, (0.09, -0.01, 1.33), (0.0, -0.3, -0.95), (-0.9, 0.2, 0.0)),
    (pre(CUT3_T), (0.09, -0.01, 1.33), (0.0, -0.3, -0.95), (-0.9, 0.2, 0.0)),
    # CUT3
    (CUT3_T, (0.095, -0.03, 1.175), (0.05, -0.35, -0.93), (-0.9, 0.1, 0.0)),
    (10.3, (0.1, -0.035, 1.16), (0.05, -0.35, -0.93), (-0.9, 0.1, 0.0)),
    (10.6, (0.095, -0.025, 1.19), (0.05, -0.35, -0.93), (-0.9, 0.1, 0.0)),
    (10.9, (0.1, -0.035, 1.165), (0.05, -0.35, -0.93), (-0.9, 0.1, 0.0)),
    (11.25, (0.27, 0.04, 1.38), (-0.7, -0.6, 0.1), (-0.2, 0.0, 0.95)),
    (11.45, (0.25, 0.05, 1.37), (-0.7, -0.6, 0.1), (-0.2, 0.0, 0.95)),
    (11.65, (0.27, 0.04, 1.38), (-0.7, -0.6, 0.1), (-0.2, 0.0, 0.95)),
    (11.85, (0.045, 0.03, 1.4), (0.3, -0.2, -0.9), (-0.5, 0.0, -0.8)),
    (12.35, (0.105, -0.01, 1.25), (0.1, -0.2, -0.97), (-0.9, 0.2, 0.0)),
    (12.75, (0.11, -0.01, 1.2), (0.05, -0.2, -0.97), (-0.9, 0.2, 0.0)),
    (13.05, (0.06, -0.115, 1.33), (-0.3, -0.3, -0.9), (0.0, 0.9, -0.3)),
    (13.35, (0.09, -0.07, 1.22), (0.0, -0.3, -0.95), (-0.9, 0.3, 0.0)),
    (13.55, (0.1, -0.04, 1.2), (0.0, -0.3, -0.95), (-0.9, 0.3, 0.0)),
    (13.95, (0.16, 0.03, 1.075), (0.1, -0.9, -0.3), (0.0, 0.0, -1.0)),
    (15.0, (0.16, 0.03, 1.072), (0.1, -0.9, -0.3), (0.0, 0.0, -1.0)),
]
for t, tip, f, p in R:
    key_hand("R", t, tip, f, p)
for t, tip, f, p in L:
    key_hand("L", t, tip, f, p)

# ---- tools ----
visible_ranges(SCISSORS, [(1.95, 7.18)])
visible_ranges(DRYER, [(7.18, pre(CUT3_T) + 1.0 / FPS)])
for piv, s in BLADES:
    key(piv, "rotation_euler", 0, (0, 0, math.radians(-s * 0.5)))
SNIPS = [2.45, 2.75, 3.8, 4.1, 4.4, 4.55, 5.25, 5.45, 6.15, 6.45, 6.75]
for ts in SNIPS:
    snip(ts)

# ---- lifted hair section ----
SECTION_RANGES = [(CUT2_T, 4.2), (5.1, 5.6), (5.95, 6.82), (8.4, 9.45)]
visible_ranges(SECTION, SECTION_RANGES)
for t, root in ((CUT2_T, (0.05, 0.0, 0.105)), (4.2, (0.05, 0.0, 0.105)), (5.1, (0.085, -0.02, 0.02)),
                (5.6, (0.085, -0.02, 0.02)), (5.95, (0.03, 0.07, 0.075)), (6.82, (0.03, 0.07, 0.075)),
                (8.4, (0.05, 0.0, 0.1)), (9.45, (0.05, 0.0, 0.1))):
    key(SECTION, "location", t, root)
st = SECTION.constraints.new("STRETCH_TO")
st.target = GRIP["L"]
st.rest_length = 1.0
st.volume = "NO_VOLUME"

# ---- falling clippings ----
C_CLIP = bpy.data.collections.new("hair_clippings")
C_HAIR.children.link(C_CLIP)
_clip_n = [0]


def clippings(t, pos, n, length, fall, spread=0.03, dur=0.55, hide_after=0.5):
    for i in range(n):
        _clip_n[0] += 1
        ln = length * rng.uniform(0.7, 1.2)
        pts = [Vector((0, 0, -ln * k / 4)) + Vector((0.006 * math.sin(k), 0, 0)) for k in range(5)]
        bm = bmesh.new()
        add_tube(bm, catmull(pts, 3), 0.006 if ln < 0.08 else 0.012, 0.004, lambda p: p - Vector((0, -1, p.z)), 6, 0.8, 0.4)
        ob = mesh_obj(f"clip_{_clip_n[0]:02d}", bm, C_CLIP, M_HAIR)
        p0 = Vector(pos) + Vector((rng.uniform(-spread, spread), rng.uniform(-spread, spread) * 0.5, rng.uniform(-spread, spread)))
        p1 = p0 + Vector((rng.uniform(-0.03, 0.03), rng.uniform(-0.04, 0.0), -fall * rng.uniform(0.85, 1.1)))
        t0 = t + rng.uniform(0.0, 0.08)
        d = dur * rng.uniform(0.85, 1.15)
        key_visible(ob, 0, False)
        key_visible(ob, t0, True)
        key_visible(ob, t0 + d + hide_after, False)
        key(ob, "location", t0, p0)
        key(ob, "location", t0 + d, p1)
        r0 = Euler((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(-3, 3)))
        key(ob, "rotation_euler", t0, r0)
        key(ob, "rotation_euler", t0 + d, Euler((r0.x + rng.uniform(-0.8, 0.8), r0.y + rng.uniform(-0.8, 0.8), r0.z)))
        fc = ob.animation_data.action.fcurves if ob.animation_data.action else []
        for fcu in ob.animation_data.action.fcurves:
            if fcu.data_path == "location":
                fcu.keyframe_points[0].interpolation = "QUAD"
                fcu.keyframe_points[0].easing = "EASE_IN"


clippings(2.45, (0.15, -0.17, 0.93), 3, 0.025, 0.1, 0.012, 0.35, 0.2)
clippings(2.75, (0.155, -0.17, 0.925), 3, 0.025, 0.1, 0.012, 0.35, 0.1)
clippings(3.8, (0.15, -0.04, 1.5), 2, 0.05, 0.3, 0.02, 0.5, 0.0)
clippings(4.1, (0.16, -0.04, 1.52), 2, 0.05, 0.3, 0.02, 0.5, 0.0)
clippings(4.55, (-0.14, -0.11, 1.0), 3, 0.2, 0.45, 0.03, 0.45, 0.0)
clippings(4.6, (0.14, -0.12, 0.98), 3, 0.2, 0.45, 0.03, 0.45, 0.0)
clippings(5.25, (0.2, -0.09, 1.23), 2, 0.04, 0.2, 0.015, 0.4, 0.05)
clippings(6.85, (-0.12, -0.08, 1.1), 3, 0.09, 0.3, 0.03, 0.45, 0.0)
clippings(6.9, (0.12, -0.08, 1.1), 3, 0.09, 0.3, 0.03, 0.45, 0.0)

# ---------------- cleanup: hard jump cuts, ease elsewhere ----------------


def iter_fcurves():
    for ad_owner in list(bpy.data.objects) + list(bpy.data.shape_keys) + list(bpy.data.materials):
        tree = getattr(ad_owner, "node_tree", None)
        for owner in (ad_owner, tree):
            if owner is None:
                continue
            ad = getattr(owner, "animation_data", None)
            if ad and ad.action:
                for fc in ad.action.fcurves:
                    yield fc


for fc in iter_fcurves():
    discrete = fc.data_path in ("hide_render", "hide_viewport")
    for kp in fc.keyframe_points:
        f = int(round(kp.co.x))
        if discrete:
            kp.interpolation = "CONSTANT"
            continue
        if f in CUT_LAST_FRAMES:
            kp.interpolation = "CONSTANT"
        if f in CUT_LAST_FRAMES or (f - 1) in CUT_LAST_FRAMES:
            kp.handle_left_type = "VECTOR"
            kp.handle_right_type = "VECTOR"
    fc.update()

# markers for the three cuts
for name, t in (("CUT1 Before / Long", 0), ("CUT2 Cutting (wet)", CUT2_T), ("long->medium", SWITCH_MED),
                ("medium->short", SWITCH_SHORT), ("Dryer", 7.5), ("CUT3 After / Short", CUT3_T),
                ("Final hold", 13.0)):
    scene.timeline_markers.new(name, frame=F(t))

notes = bpy.data.texts.new("PREVIS_NOTES")
notes.write(__doc__)

# ---------------- reach check ----------------


def reach_report():
    worst = []
    for side, data in (("R", R), ("L", L)):
        for t, *_ in data:
            scene.frame_set(F(t))
            dg = bpy.context.evaluated_depsgraph_get()
            re = RIG.evaluated_get(dg)
            pb = re.pose.bones[f"forearm.{side}"]
            wrist_bone = re.matrix_world @ pb.tail
            wrist_tgt = IK[side].evaluated_get(dg).matrix_world.translation
            gap = (wrist_bone - wrist_tgt).length
            if gap > 0.01:
                worst.append((round(gap, 3), side, t))
    worst.sort(reverse=True)
    print("IK gaps > 1cm (gap, side, t):", worst[:12])
    scene.frame_set(1)


reach_report()

# ==========================================================================
# Save / render
# ==========================================================================
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, compress=True)
print("saved", BLEND_PATH)


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


res = int(arg("--res", "1920"))
scene.render.resolution_x = res
scene.render.resolution_y = res * 9 // 16
scene.cycles.samples = int(arg("--samples", "24"))

if arg("--stills"):
    out = arg("--stills")
    os.makedirs(out, exist_ok=True)
    times = [float(x) for x in arg("--times", "1.0,2.5,3.5,5.3,6.4,8.5,11.5,14.5").split(",")]
    for t in times:
        scene.frame_set(F(t))
        scene.render.filepath = os.path.join(out, f"still_{t:05.2f}s.png")
        bpy.ops.render.render(write_still=True)
        print("still", t)

if arg("--render"):
    out = arg("--render")
    os.makedirs(out, exist_ok=True)
    scene.frame_start = int(arg("--start", "1"))
    scene.frame_end = int(arg("--end", str(FRAME_END)))
    scene.render.filepath = os.path.join(out, "f_")
    bpy.ops.render.render(animation=True)
