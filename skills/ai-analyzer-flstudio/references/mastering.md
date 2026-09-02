# Mastering Diagnostic Reference

Mastering 不以“达到某个固定 LUFS”为唯一目标。

优先看：

1. Musical balance
2. Tonal balance
3. Macro dynamics
4. True Peak
5. LUFS-S / LUFS-I
6. Stereo integrity
7. Translation

常见组合：

## LUFS 很高 + Crest 很低

可能：

- limiter/compression 较重
- clipping 较多
- arrangement 本身很密

不要自动要求降低响度，先听风格和参考。

## True Peak 接近 0 dBTP

可能：

- codec headroom 不足

优先检查 limiter ceiling / oversampling / clipping chain。

## LUFS-I 使用注意

只有在 Analyzer 从头完整累计目标节目后，才适合作为完整节目 integrated loudness。

局部循环测到的 LUFS-I 只代表那个累计范围。
