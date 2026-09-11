# 全部本轮试验

单位：秒/点。不同批次不直接比较均值；各行均有自己的同场baseline。

| 运行 | 候选均值与完整性 | 布局/误差 |
|---|---|---|
| R001-smoke | baseline 241.6814（8/8全清）；projection 241.5688（8/8全清）；cost 239.5584（8/8全清）；shared 242.6957（8/8全清）；mid_search 242.6957（8/8全清） | uniform area / sin |
| R002-cost-variants | baseline 231.6114（12/12全清）；mean 230.4696（12/12全清）；max 228.8567（12/12全清）；exact 230.3964（12/12全清）；exit 230.3205（12/12全清） | uniform area / sin |
| R003-merge-scan | baseline 233.1332（20/20全清）；merged 233.1332（20/20全清）；merged3 233.2291（20/20全清） | uniform area / sin |
| R004-merge-target-scans | baseline 233.1332（20/20全清）；merge_targets 231.5621（20/20全清）；merge_targets3 231.3940（20/20全清） | uniform area / sin |
| R005-validation | baseline 248.4391（40/40全清）；cost_max 246.3175（40/40全清）；merge3 246.8630（40/40全清）；combined 243.9459（40/40全清） | uniform area / sin |
| R006-edge-plus | baseline 219.4156（8/8全清）；cost_max 219.0991（8/8全清）；merge3 216.8687（8/8全清）；combined 216.5553（8/8全清） | edge / plus |
| R007-edge-minus | baseline 216.4680（8/8全清）；cost_max 216.4290（8/8全清）；merge3 215.4536（8/8全清）；combined 215.3997（8/8全清） | edge / minus |
| R008-edge-checker | baseline 212.5608（8/8全清）；cost_max 212.6337（8/8全清）；merge3 212.5608（8/8全清）；combined 212.6337（8/8全清） | edge / checker |
| R009-frozen-audit | baseline 244.0157（100/100全清）；combined 242.5808（100/100全清） | uniform area / sin |
