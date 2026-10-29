import math
import wave
import numpy as np

# Load slot 0 raw IR
with wave.open("C:/Users/wizardbeard/AppData/Roaming/REAPER/Data/sepulchre_irs/01_BlackWizard_Center.wav", "rb") as wf:
    raw = wf.readframes(wf.getnframes())
    raw_ir = np.array([int.from_bytes(raw[i*3:i*3+3], "little", signed=True) / 8388608.0 for i in range(wf.getnframes())])

srate = 48000.0
ir_srate = 44100.0
isc = ir_srate / srate
ir_len = min(2048, int(len(raw_ir) / isc))

# Linear interpolation resampler exactly matching prepare_ir_fft() in JSFX
resampled_ir = np.zeros(ir_len)
for i in range(ir_len):
    ipos = int(i * isc)
    frac = i * isc - ipos
    p0 = raw_ir[ipos]
    p1 = raw_ir[min(len(raw_ir) - 1, ipos + 1)]
    resampled_ir[i] = p0 * (1.0 - frac) + p1 * frac

def bq_hp(freq, q, sr):
    w0 = 2 * math.pi * freq / sr
    alpha = math.sin(w0) / (2 * q)
    cosw0 = math.cos(w0)
    b0 = (1 + cosw0) / 2
    b1 = -(1 + cosw0)
    b2 = (1 + cosw0) / 2
    a0 = 1 + alpha
    a1 = -2 * cosw0
    a2 = 1 - alpha
    return np.array([b0/a0, b1/a0, b2/a0, a1/a0, a2/a0])

def bq_lp(freq, q, sr):
    w0 = 2 * math.pi * freq / sr
    alpha = math.sin(w0) / (2 * q)
    cosw0 = math.cos(w0)
    b0 = (1 - cosw0) / 2
    b1 = 1 - cosw0
    b2 = (1 - cosw0) / 2
    a0 = 1 + alpha
    a1 = -2 * cosw0
    a2 = 1 - alpha
    return np.array([b0/a0, b1/a0, b2/a0, a1/a0, a2/a0])

def bq_ls(freq, gain_db, sr):
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2 * math.pi * freq / sr
    cosw0 = math.cos(w0)
    sinw0 = math.sin(w0)
    alpha = sinw0 / 2.0 * math.sqrt(2.0)
    b0 = A * ((A + 1) - (A - 1) * cosw0 + 2 * math.sqrt(A) * alpha)
    b1 = 2 * A * ((A - 1) - (A + 1) * cosw0)
    b2 = A * ((A + 1) - (A - 1) * cosw0 - 2 * math.sqrt(A) * alpha)
    a0 = (A + 1) + (A - 1) * cosw0 + 2 * math.sqrt(A) * alpha
    a1 = -2 * ((A - 1) + (A + 1) * cosw0)
    a2 = (A + 1) + (A - 1) * cosw0 - 2 * math.sqrt(A) * alpha
    return np.array([b0/a0, b1/a0, b2/a0, a1/a0, a2/a0])

def apply_bq(b, x):
    y = np.zeros_like(x)
    s1 = s2 = 0.0
    for i in range(len(x)):
        v = x[i]
        out = b[0] * v + s1
        s1 = b[1] * v - b[3] * out + s2
        s2 = b[2] * v - b[4] * out
        y[i] = out
    return y

# Exactly reproduce prepare_ir_fft energy calculation
n = ir_len + 2048
scratch = np.zeros(n)
scratch[:ir_len] = resampled_ir
cab_hp = bq_hp(85.0, 0.7071, srate)
irw1 = bq_hp(90.0, 0.7071, srate)
irw2 = bq_ls(500.0, 12.0, srate)
irw3 = bq_lp(6000.0, 0.7071, srate)

scratch = apply_bq(cab_hp, scratch)
scratch = apply_bq(irw1, scratch)
scratch = apply_bq(irw2, scratch)
scratch = apply_bq(irw3, scratch)

e = np.sum(scratch ** 2)
IR_E48 = 0.283543
norm_g = math.sqrt(IR_E48 * (48000.0 / srate) / e) if e > 1e-10 else 1.0

# Input signal: impulse from impulse.wav through bq_in_hp (40 Hz HPF)
x_in = np.zeros(4096)
x_in[0] = 0.7069998979568481
in_hp = bq_hp(40.0, 0.7071, srate)
x_filtered = apply_bq(in_hp, x_in)

# Direct convolution with normalized IR
conv_out = np.convolve(x_filtered, resampled_ir * norm_g)[:4096]

# Post-convolution cab_hp (85 Hz)
expected = apply_bq(cab_hp, conv_out)

# Read rendered out_impulse.wav (where latency is 128 samples)
with wave.open("D:/VSTs/sepulchre_sound/tests/render/out_impulse.wav", "rb") as wf:
    raw = wf.readframes(3000)
    rendered = np.array([int.from_bytes(raw[i*6:i*6+3], "little", signed=True) / 8388608.0 for i in range(wf.getnframes())])

rend_seg = rendered[128 : 128 + 2048]
exp_seg = expected[:2048]

diff = rend_seg - exp_seg
max_err = np.max(np.abs(diff))
sig_peak = np.max(np.abs(exp_seg))
null_db = 20 * math.log10(max_err / sig_peak)
rms_diff = math.sqrt(np.mean(diff ** 2))
rms_sig = math.sqrt(np.mean(exp_seg ** 2))
null_rms_db = 20 * math.log10(rms_diff / rms_sig)

print(f"Signal Peak: {sig_peak:.6f}")
print(f"Max Absolute Error: {max_err:.3e}")
print(f"Peak Null vs Expected Signal: {null_db:.2f} dB")
print(f"RMS Null vs Expected Signal:  {null_rms_db:.2f} dB")
