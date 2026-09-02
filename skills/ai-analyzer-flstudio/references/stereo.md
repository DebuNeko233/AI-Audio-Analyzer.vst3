# Stereo / Mono Compatibility Reference

Correlation：

```text
+1    strongly correlated / mono-like
 0    weakly correlated / wide
<0    phase cancellation risk
```

但 correlation 不能脱离能量判断。

如果某频段几乎无声：

- correlation 数字可能不稳定
- 不应据此大改 mix

低频检查顺序：

```text
20–60 Hz
60–120 Hz
120–250 Hz
```

如果低频能量较强且 correlation 为负：

1. 检查 stereo bass source
2. 检查 chorus/unison
3. 检查 Haas/micro delay
4. 检查 M/S processing
5. 检查 stereo reverb low end
6. 再考虑 mono-maker / side EQ
