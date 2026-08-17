from __future__ import annotations

import math
import os
import subprocess
import wave
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DURATION = 720, 1280, 30, 60
ROOT = Path(__file__).parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
VIDEO = OUT / "mitosis_no_audio.mp4"
FINAL = OUT / "mitosis.mp4"
AUDIO = OUT / "soundtrack.wav"


def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


F_BIG, F_MED, F_SMALL = font(66, True), font(42, True), font(30, False)


def ease(t):
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * ease(max(0, min(1, t)))


def scene_for(t):
    if t < 4: return 0, t / 4
    if t < 12: return 1, (t - 4) / 8
    if t < 22: return 2, (t - 12) / 10
    if t < 34: return 3, (t - 22) / 12
    if t < 46: return 4, (t - 34) / 12
    return 5, (t - 46) / 14


def base():
    y = np.linspace(0, 1, H)[:, None]
    top = np.array([13, 10, 32], float)
    bottom = np.array([47, 17, 62], float)
    arr = np.repeat((top * (1-y) + bottom * y)[:, None, :], W, axis=1)
    return Image.fromarray(np.uint8(arr), "RGB")


def bubble(d, x, y, r, fill, outline=(255,255,255), width=5):
    d.ellipse((x-r,y-r,x+r,y+r), fill=fill, outline=outline, width=width)


def chromosome(d, x, y, scale=1.0, angle=0, face=True, duplicate=False):
    # Compact X-shaped cartoon chromosome.
    pts = [(-45,-65), (-12,-18), (-45,65), (-22,78), (0,28), (22,78), (45,65), (12,-18), (45,-65), (22,-78), (0,-28), (-22,-78)]
    pts = [(x+px*scale, y+py*scale) for px,py in pts]
    d.polygon(pts, fill=(240,100,170), outline=(255,225,245))
    if face:
        bubble(d, x-13*scale, y-7*scale, 5*scale, (20,15,35), outline=(20,15,35), width=1)
        bubble(d, x+13*scale, y-7*scale, 5*scale, (20,15,35), outline=(20,15,35), width=1)
        d.arc((x-18*scale,y+2*scale,x+18*scale,y+25*scale), 10, 170, fill=(20,15,35), width=max(1,int(4*scale)))


def text_center(d, text, y, f=F_MED, fill=(255,255,255)):
    box = d.textbbox((0,0), text, font=f)
    d.text(((W-(box[2]-box[0]))/2, y), text, font=f, fill=fill)


def caption(d, text):
    # Dark rounded caption bar for TikTok readability.
    box = d.multiline_textbbox((0,0), text, font=F_MED, spacing=8, align="center")
    tw, th = box[2]-box[0], box[3]-box[1]
    x = (W-tw)//2
    y = H-210
    d.rounded_rectangle((x-28,y-20,x+tw+28,y+th+20), radius=24, fill=(7,5,18,225))
    d.multiline_text((x,y), text, font=F_MED, fill=(255,255,255), spacing=8, align="center")


def draw_frame(t):
    img = base().convert("RGBA")
    d = ImageDraw.Draw(img)
    scene, p = scene_for(t)
    cx, cy = W//2, 620

    # Floating particles make the scene feel alive.
    for i in range(22):
        x = (i*97 + int(t*35)) % W
        y = (i*173 + int(t*22)) % H
        r = 3 + (i % 3)
        d.ellipse((x-r,y-r,x+r,y+r), fill=(255,255,255,90))

    if scene == 0:
        # Hook: innocent cell, then sudden ominous zoom.
        r = int(255 + 20*math.sin(t*4))
        bubble(d, cx, cy, r, (71,185,244,170), width=9)
        bubble(d, cx, cy, 110, (93,58,160,210), width=7)
        chromosome(d, cx, cy, 1.0)
        text_center(d, "POV: your cell wants a clone", 120, F_MED)
        if p > .55: caption(d, "bro... something is happening 💀")

    elif scene == 1:
        # Duplicate appears from behind.
        bubble(d, cx, cy, 270, (71,185,244,150), width=9)
        bubble(d, cx, cy, 105, (93,58,160,210), width=7)
        offset = lerp(0, 180, p)
        chromosome(d, cx-offset, cy, .9)
        chromosome(d, cx+offset, cy, .9)
        if p > .65:
            caption(d, "WAIT... WHO ARE YOU?!")
        else:
            caption(d, "why are there TWO of me?")

    elif scene == 2:
        # Replication chaos: multiple chromosomes pop in.
        bubble(d, cx, cy, 300, (71,185,244,145), width=9)
        bubble(d, cx, cy, 105, (93,58,160,210), width=7)
        positions = [(-115,-95),(115,-95),(-115,95),(115,95)]
        for i,(dx,dy) in enumerate(positions):
            s = .72 + .12*math.sin(t*8+i)
            chromosome(d, cx+dx, cy+dy, s)
        text_center(d, "DNA: COPIED", 110, F_MED, (255,235,90))
        caption(d, "the cell just duplicated the blueprint 😭")

    elif scene == 3:
        # Spindle fibers pull chromosomes apart.
        bubble(d, cx, cy, 310, (71,185,244,125), width=9)
        left, right = 120, W-120
        for yy in (500,620,740):
            d.line((left,yy,cx,cy), fill=(255,245,150,180), width=6)
            d.line((right,yy,cx,cy), fill=(255,245,150,180), width=6)
        separation = lerp(0, 235, p)
        chromosome(d, cx-separation, cy, .9)
        chromosome(d, cx+separation, cy, .9)
        if p < .35:
            caption(d, "WHY IS THE CELL PULLING ME?!")
        else:
            caption(d, "BRO LET GO 😭")

    elif scene == 4:
        # Cell pinches into two.
        pinch = lerp(0, 180, p)
        leftx, rightx = cx-150-pinch/3, cx+150+pinch/3
        bubble(d, leftx, cy, 205, (71,185,244,150), width=9)
        bubble(d, rightx, cy, 205, (71,185,244,150), width=9)
        chromosome(d, leftx, cy, .72)
        chromosome(d, rightx, cy, .72)
        text_center(d, "SPLIT", 120, F_MED, (255,220,100))
        if p > .55: caption(d, "WAIT... DID WE JUST CLONE OURSELVES?")

    else:
        # Final reveal.
        bubble(d, cx-175, cy, 205, (71,185,244,170), width=9)
        bubble(d, cx+175, cy, 205, (71,185,244,170), width=9)
        chromosome(d, cx-175, cy, .72)
        chromosome(d, cx+175, cy, .72)
        text_center(d, "1 CELL  →  2 CELLS", 110, F_BIG, (255,235,90))
        if p < .45:
            caption(d, "Yep. That's basically MITOSIS.")
        else:
            caption(d, "so... we're twins?\nUnfortunately. 💀")

    return img.convert("RGB")


def make_audio(path: Path):
    # Procedural cartoon soundtrack: no copyrighted music or external assets.
    sr = 44100
    n = int(DURATION * sr)
    audio = np.zeros(n, dtype=np.float32)

    def add_tone(start, dur, freq, amp=.18, sweep=0):
        a = max(0, int(start*sr)); b = min(n, int((start+dur)*sr))
        if b <= a: return
        tt = np.arange(b-a)/sr
        f = freq + sweep*tt/dur
        sig = np.sin(2*np.pi*f*tt) * amp * np.exp(-2.8*tt/dur)
        audio[a:b] += sig

    def add_noise_burst(start, dur, amp=.12):
        a=max(0,int(start*sr)); b=min(n,int((start+dur)*sr))
        if b<=a:return
        rng=np.random.default_rng(int(start*1000)+7)
        tt=np.arange(b-a)/sr
        audio[a:b]+=rng.normal(0,1,b-a).astype(np.float32)*amp*np.exp(-18*tt)

    # Hook boom, record scratch, pops, tension, split, final sting.
    add_tone(0.0,.55,70,.42,-35); add_noise_burst(.05,.45,.20)
    add_tone(5.7,.18,900,.18,500)
    add_tone(12.0,.25,160,.25,300)
    for s in (22,24.2,26.4,28.6,30.8):
        add_tone(s,.35,120,.24,420); add_noise_burst(s,.16,.10)
    add_tone(34.0,.7,90,.35,-40); add_noise_burst(34.1,.5,.18)
    add_tone(44.8,.28,1100,.25,-600)
    add_tone(55.0,.8,520,.18,900)
    add_tone(59.1,.7,65,.38,-20)
    # subtle pulse throughout
    for s in np.arange(0,60,1.0):
        add_tone(float(s),.07,110,.045)

    audio=np.clip(audio,-.95,.95)
    pcm=(audio*32767).astype(np.int16)
    with wave.open(str(path),'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(pcm.tobytes())


def render():
    writer=imageio.get_writer(str(VIDEO), fps=FPS, codec="libx264", quality=8, macro_block_size=1)
    total=FPS*DURATION
    for i in range(total):
        writer.append_data(np.asarray(draw_frame(i/FPS)))
        if i % FPS == 0: print(f"rendered {i/FPS:.0f}s/{DURATION}s")
    writer.close()
    make_audio(AUDIO)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg,"-y","-i",str(VIDEO),"-i",str(AUDIO),"-c:v","copy","-c:a","aac","-b:a","160k","-shortest",str(FINAL)],check=True)
    print(f"Created {FINAL}")


if __name__ == "__main__":
    import imageio_ffmpeg
    render()
