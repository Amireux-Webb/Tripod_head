import numpy as np
import matplotlib.pyplot as plt
import os
from os.path import join
from utils.logger import logger


def gen_up_chirp(
    samp_rate: float, SF: int, BW: float, avg_power=1.0
) -> tuple[np.ndarray[np.complex128], np.ndarray[np.float64]]:
    sym_toa = 2**SF / BW
    k = BW / sym_toa
    t = np.arange(0, sym_toa, 1 / samp_rate)
    sig = np.sqrt(avg_power) * np.exp(1j * 2 * np.pi * (-BW / 2 + k / 2 * t) * t)
    return sig, t


def gen_down_chirp(
    samp_rate: float, SF: int, BW: float, avg_power=1.0
) -> tuple[np.ndarray[np.complex128], np.ndarray[np.float64]]:
    sym_toa = 2**SF / BW
    k = BW / sym_toa
    t = np.arange(0, sym_toa, 1 / samp_rate)
    sig = np.sqrt(avg_power) * np.exp(1j * 2 * np.pi * (BW / 2 - k / 2 * t) * t)
    return sig, t


def gen_chirp(
    samp_rate: float, sym_length: int, BW: float
) -> tuple[np.ndarray[np.complex128], np.ndarray[np.float64]]:
    sym_toa = sym_length / samp_rate
    k = BW / sym_toa
    t = np.arange(0, sym_toa, 1 / samp_rate)
    sig = np.exp(1j * 2 * np.pi * (-BW / 2 + k / 2 * t) * t)
    return sig, t


def gen_preamble(
    samp_rate: float, SF: int, BW: float, preamble_len: int
) -> tuple[np.ndarray[np.complex64], np.ndarray[np.float64]]:
    up_chirp, t_chirp = gen_up_chirp(samp_rate, SF, BW)
    sig = np.tile(up_chirp, preamble_len)
    t = t_chirp
    for _ in range(preamble_len - 1):
        t_end = t[-1]
        t = np.concatenate((t, t_chirp + t_end))
    return sig, t


def gen_sine_wave(sample_rate: float, freq: float, duration: float):
    t = np.arange(0, duration, 1 / sample_rate)
    return np.exp(1j * 2 * np.pi * freq * t), t


def gen_unit_noise(sig_size: int) -> np.ndarray[np.complex64]:
    real = np.random.randn(sig_size)
    imag = np.random.randn(sig_size)
    return (real + 1j * imag) / np.sqrt(2)
    
def add_noise(
    SNR: int,
    sig: np.ndarray[np.complex64] | np.ndarray[np.complex128],
    sig_power=None,
    unit_noise=None,
    silent = False,
) -> np.ndarray[np.complex64] | np.ndarray[np.complex128]:
    if sig_power is None:
        sig_power = np.mean(np.abs(sig) ** 2)
    noise_power = sig_power / (10 ** (SNR / 10))
    if not silent:
        logger.info("[1/3] Creating Noise...")
    if unit_noise is None:
        sig_size = sig.size
        real = np.random.randn(sig_size)
        imag = np.random.randn(sig_size)
        unit_noise = (real + 1j * imag) / np.sqrt(2)
    noise = (unit_noise * np.sqrt(noise_power)).astype(sig.dtype)
    if not silent:
        logger.info("[2/3] Adding Noise...")
    out_sig = sig + noise
    if not silent:
        logger.info("[3/3] Normalizing...")
    out_sig /= np.max(np.abs(out_sig))
    if not silent:
        logger.info(
            f"SNR: {SNR}, Sig dtype: {sig.dtype}, Sig power: {sig_power}, Noise power: {noise_power}"
        )
    return out_sig


def analysis(
    sig: np.ndarray[np.complex64],
    t: np.ndarray[np.float64],
    output_dir: str,
    fig_size=(80, 20),
    zero_padding=1,
):
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output dir: {output_dir!r}")
    duration = t[-1] - t[0]
    samp_rate = 1 / (t[1] - t[0])
    with open(join(output_dir, "sig.cfile"), "wb") as of:
        sig.astype(np.complex64).tofile(of)
    sig_timedomain = np.abs(sig) * np.cos(np.angle(sig))
    if zero_padding < 0:
        logger.error(f"Invalid zero_padding: {zero_padding}")
        return
    sig_padded_size = (zero_padding + 1) * sig.size
    spectrum = np.fft.fft(sig * np.hanning(sig.size), n=sig_padded_size)
    fft_freq = np.fft.fftfreq(sig_padded_size, t[1] - t[0])
    fft_info = f"FFT freq_range={np.min(fft_freq)} Hz - {np.max(fft_freq)} Hz, num_of_bins={fft_freq.size}"
    logger.info(
        f"Duration: {duration}, Sample rate: {samp_rate}, sig.size: {sig.size}, Zero padding: {zero_padding}, num_of_bins={fft_freq.size}"
    )
    logger.info(fft_info)
    plt.figure(figsize=fig_size)
    plt.plot(fft_freq, np.abs(spectrum), "ro")
    plt.xlabel(fft_info)
    plt.ylabel("Amplitude")
    plt.xticks(np.arange(-samp_rate / 2, samp_rate / 2, samp_rate / 30))
    plt.title("Spectrum")
    plt.savefig(join(output_dir, "spectrum.png"))
    logger.info(f"Saved spectrum to {join(output_dir, 'spectrum.png')!r}")
    plt.close()
    plt.figure(figsize=fig_size)
    plt.plot(t, sig_timedomain)
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title("Time Domain")
    plt.savefig(join(output_dir, "time_domain.png"))
    logger.info(f"Saved time domain to {join(output_dir, 'time_domain.png')!r}")
    plt.figure()
    plt.close()
    plt.figure(figsize=fig_size)
    plt.plot(t, np.real(sig), label="Real part")
    plt.plot(t, np.imag(sig), label="Imaginary part")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title("Complex Sinusoidal Signal")
    plt.legend()
    plt.grid()
    plt.savefig(join(output_dir, "time_domain_complex.png"))
    logger.info(
        f"Saved complex time domain to {join(output_dir, 'time_domain_complex.png')!r}"
    )
    plt.close()
    return output_dir


def down_sample(
    sig: np.ndarray[np.complex64] | np.ndarray[np.complex128], factor: int
) -> np.ndarray[np.complex64] | np.ndarray[np.complex128]:
    logger.info(f"Downsampling factor: {factor}")
    return sig[::factor]


def slicing(
    intput: np.ndarray[np.complex64], slicing_len
) -> np.ndarray[np.complex64, np.complex64]:
    logger.info(f"{intput.shape=}, {slicing_len=}")
    res_len = intput.size
    slices_num = res_len // slicing_len + int(res_len % slicing_len != 0)
    res_sliced = np.zeros((slices_num, slicing_len), dtype=np.complex64)
    for i in range(slices_num):
        start_idx = i * slicing_len
        end_idx = min(start_idx + slicing_len, res_len)
        res_sliced[i, : end_idx - start_idx] = intput[start_idx:end_idx]
    return res_sliced


def slicing_float(
    intput: np.ndarray[np.float64], slicing_len
) -> np.ndarray[np.float64, np.float64]:
    logger.info(f"{intput.shape=}, {slicing_len=}")
    res_len = intput.size
    slices_num = res_len // slicing_len + int(res_len % slicing_len != 0)
    res_sliced = np.zeros((slices_num, slicing_len), dtype=np.float64)
    for i in range(slices_num):
        start_idx = i * slicing_len
        end_idx = min(start_idx + slicing_len, res_len)
        res_sliced[i, : end_idx - start_idx] = intput[start_idx:end_idx]
    return res_sliced


def linear_func(x, m, b):
    return m * x + b
