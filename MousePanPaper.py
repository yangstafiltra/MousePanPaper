#!/usr/bin/env python3
"""
MousePanPaper - mpvpaper 鼠标跟随视差滚动
"""

import os, sys, json, time, subprocess, socket, signal

EASE_PRESETS = {
    "linear": (0.0, 0.0, 1.0, 1.0),
    "in":     (0.55, 0.06, 0.68, 0.19),
    "out":    (0.25, 0.46, 0.45, 0.94),
    "in-out": (0.42, 0.0, 0.58, 1.0),
}

SOCK_PATH = "/tmp/mpvpaper.sock"
MAX_PAN = 0.015
SMOOTH = 0.08
INTERVAL_MS = 16
FS_DISABLE = False
EXCLUDE = {"kitty", "kitty-dropterm"}
BLUR = False
SCALE = 1.05
EASE = EASE_PRESETS["in-out"]
DEBUG = False

USAGE = f"""用法: {sys.argv[0]} [选项]

选项:
  -m, --max-pan NUM   最大偏移 (默认 {MAX_PAN})
  -s, --smooth NUM    平滑系数 0~1，越小越平滑 (默认 {SMOOTH})
  -i, --interval MS   轮询间隔 (默认 {INTERVAL_MS})
  -p, --path PATH     IPC 套接字路径 (默认 {SOCK_PATH})
  -f, --fs-disable     全屏时自动禁用
  -e, --exclude CLASS  排除的窗口类 (可重复)
  -b, --blur           动态模糊
  -z, --zoom NUM       壁纸放大倍率 (默认 {SCALE}, 1.0=原大)
  --ease TYPE/CP     缓动曲线: linear/in/out/in-out 或 x1,y1,x2,y2 (默认 in-out)
  -d, --debug         调试输出
  -h, --help          帮助"""

def parse_args():
    global MAX_PAN, SMOOTH, INTERVAL_MS, SOCK_PATH, FS_DISABLE, EXCLUDE, BLUR, SCALE, EASE, DEBUG
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a in ("-h", "--help"): print(USAGE); sys.exit(0)
        elif a in ("-m", "--max-pan") and i+1 < len(sys.argv): MAX_PAN = max(0.0, float(sys.argv[i+1])); i += 2
        elif a in ("-s", "--smooth") and i+1 < len(sys.argv): SMOOTH = max(0.001, min(1, float(sys.argv[i+1]))); i += 2
        elif a in ("-i", "--interval") and i+1 < len(sys.argv): INTERVAL_MS = max(8, int(sys.argv[i+1])); i += 2
        elif a in ("-p", "--path") and i+1 < len(sys.argv): SOCK_PATH = sys.argv[i+1]; i += 2
        elif a in ("-f", "--fs-disable"): FS_DISABLE = True; i += 1
        elif a in ("-e", "--exclude") and i+1 < len(sys.argv): EXCLUDE.add(sys.argv[i+1]); i += 2
        elif a in ("-b", "--blur"): BLUR = True; i += 1
        elif a == "--ease" and i+1 < len(sys.argv):
            v = sys.argv[i+1]
            if v in EASE_PRESETS:
                EASE = EASE_PRESETS[v]
            else:
                try:
                    p = tuple(float(x) for x in v.split(","))
                    if len(p) != 4: raise ValueError
                    EASE = p
                except:
                    print(f"无效 --ease: {v}", file=sys.stderr)
                    sys.exit(1)
            i += 2
        elif a in ("-z", "--zoom") and i+1 < len(sys.argv): SCALE = max(1.0, float(sys.argv[i+1])); i += 2
        elif a in ("-d", "--debug"): DEBUG = True; i += 1
        else: print(f"未知: {a}", file=sys.stderr); sys.exit(1)

def dbg(msg):
    if DEBUG:
        print(f"  {msg}", flush=True)

class IPC:
    def __init__(self, path):
        self.path = path
    def cmd(self, msg):
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(self.path)
            s.send(json.dumps(msg).encode() + b"\n")
            r = s.recv(4096).decode()
            s.close()
            return json.loads(r) if r else {}
        except:
            return {"error": "fail"}
    def set(self, prop, val):
        return self.cmd({"command": ["set_property", prop, val]})
    def get(self, prop):
        return self.cmd({"command": ["get_property", prop]}).get("data")

def cubic_bezier(x, x1, y1, x2, y2):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    t = x
    for _ in range(8):
        bx = 3*(1-t)**2*t*x1 + 3*(1-t)*t**2*x2 + t**3
        dx = 3*(1-t)**2*(x1) + 6*(1-t)*t*(x2-x1) + 3*t**2*(1-x2)
        if abs(bx - x) < 1e-6: break
        t -= (bx - x) / dx
        t = max(0.0, min(1.0, t))
    return 3*(1-t)**2*t*y1 + 3*(1-t)*t**2*y2 + t**3

def get_mouse():
    try:
        r = subprocess.run(["hyprctl", "cursorpos"], capture_output=True, text=True, timeout=1)
        x, y = r.stdout.strip().split(",")
        return int(x), int(y.strip())
    except:
        return None

def get_screen_size():
    try:
        r = subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True, text=True, timeout=1)
        monitors = json.loads(r.stdout)
        if monitors:
            return monitors[0]["width"], monitors[0]["height"]
    except:
        pass
    return 1920, 1080

def get_active_ws():
    try:
        r = subprocess.run(["hyprctl", "activeworkspace", "-j"], capture_output=True, text=True, timeout=1)
        return json.loads(r.stdout).get("id")
    except:
        return None

def is_fullscreen(ws):
    if ws is None: return False
    try:
        r = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True, text=True, timeout=1)
        for c in json.loads(r.stdout):
            if (c.get("fullscreen", 0) and c.get("mapped", True)
                and c.get("workspace", {}).get("id") == ws
                and c.get("class", "").lower() not in EXCLUDE):
                return True
        return False
    except:
        return False

def main():
    parse_args()
    dt = INTERVAL_MS / 1000.0

    ipc = IPC(SOCK_PATH)
    if not os.path.exists(SOCK_PATH):
        print(f"错误: 未找到 {SOCK_PATH}\n请先启动 mpvpaper 并带 --input-ipc-server={SOCK_PATH}")
        sys.exit(1)
    if ipc.get("video-pan-x") is None:
        print("错误: IPC 连接失败")
        sys.exit(1)

    screen_w, screen_h = get_screen_size()
    dbg(f"分辨率: {screen_w}x{screen_h}")

    if SCALE != 1.0:
        ipc.set("video-scale-x", SCALE)
        ipc.set("video-scale-y", SCALE)
        dbg(f"缩放: {SCALE}")

    if BLUR:
        r = ipc.cmd({"command": ["set", "vf", "lavfi=[tmix=frames=3:weights=1+2+1]"]})
        dbg(f"模糊: {'ok' if 'error' not in r else str(r)}")

    pan_x = pan_y = 0.0
    sm_x = sm_y = 0.0
    last_pan_x = last_pan_y = None
    last_fs_check = 0.0
    fs_active = False
    running = True

    def cleanup(*_):
        nonlocal running
        ipc.set("video-pan-x", 0.0)
        ipc.set("video-pan-y", 0.0)
        if SCALE != 1.0:
            ipc.set("video-scale-x", 1.0)
            ipc.set("video-scale-y", 1.0)
        if BLUR:
            ipc.cmd({"command": ["set", "vf", ""]})
        running = False

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    ep = EASE
    ease_label = next((k for k, v in EASE_PRESETS.items() if v == ep), f"{ep[0]},{ep[1]},{ep[2]},{ep[3]}")
    print(f"MousePanPaper  偏移={MAX_PAN}  缩放={SCALE}  缓动={ease_label}  平滑={SMOOTH}  间隔={INTERVAL_MS}ms  全屏禁用={'是' if FS_DISABLE else '否'}")

    while running:
        try:
            now = time.monotonic()

            if FS_DISABLE and now - last_fs_check > 0.3:
                ws = get_active_ws()
                fs_active = is_fullscreen(ws)
                last_fs_check = now

            pos = get_mouse()
            if pos:
                mx, my = pos
                if sm_x == 0 and sm_y == 0:
                    sm_x, sm_y = float(mx), float(my)

                sm_x += (mx - sm_x) * SMOOTH
                sm_y += (my - sm_y) * SMOOTH

                if abs(mx - sm_x) <= 0.3:
                    sm_x = float(mx)
                if abs(my - sm_y) <= 0.3:
                    sm_y = float(my)

                rel_x = sm_x / screen_w
                rel_y = sm_y / screen_h
                rel_x = max(0, min(1, rel_x))
                rel_y = max(0, min(1, rel_y))

                if fs_active:
                    tgt_x = 0.0
                    tgt_y = 0.0
                else:
                    tgt_x = (rel_x - 0.5) * MAX_PAN * 2
                    tgt_y = (rel_y - 0.5) * MAX_PAN * 2

                ease_t = cubic_bezier(min(1.0, dt / 0.05), *EASE)
                pan_x += (tgt_x - pan_x) * ease_t
                pan_y += (tgt_y - pan_y) * ease_t

                if abs(pan_x - tgt_x) < 0.00001:
                    pan_x = tgt_x
                if abs(pan_y - tgt_y) < 0.00001:
                    pan_y = tgt_y

                if abs(pan_x) < 0.00005:
                    pan_x = 0.0
                if abs(pan_y) < 0.00005:
                    pan_y = 0.0

                rpan_x = round(pan_x, 6)
                rpan_y = round(pan_y, 6)
                if rpan_x != last_pan_x or rpan_y != last_pan_y:
                    ipc.set("video-pan-x", rpan_x)
                    ipc.set("video-pan-y", rpan_y)
                    last_pan_x, last_pan_y = rpan_x, rpan_y

                if DEBUG and int(now * 10) % 5 == 0:
                    print(f"\r  鼠标=({int(sm_x)},{int(sm_y)})  pan=({pan_x:.5f},{pan_y:.5f})  fs={fs_active}", end="", flush=True)

            time.sleep(dt)

        except KeyboardInterrupt:
            cleanup()
            break
        except Exception as e:
            dbg(f"err: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
