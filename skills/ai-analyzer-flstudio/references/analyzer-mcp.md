# AI Analyzer MCP Reference

当前主要工具：

```text
audio_list_tracks()
audio_snapshot(track)
audio_average(track, seconds=5)
audio_stereo_bands(track)
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
audio_master_status(track="Master")
```

推荐调用策略：

```text
单轨快速检查
audio_list_tracks
→ audio_average(track, 5)

Master
audio_master_status
→ audio_average("Master", 10)
→ audio_stereo_bands("Master")

双轨冲突
audio_average(A, 5)
→ audio_average(B, 5)
→ audio_compare_tracks(A, B)
→ audio_detect_masking(A, B)
```

不要用单帧 snapshot 代替稳定的混音判断，除非用户明确要求瞬时状态。
