# 外部物性来源

纯水液相至汽相焓差与饱和蒸气压取自NISTIR 5078 Table 1，基于IAPWS公式，2026-09-11访问。

https://www.nist.gov/document/nistir5078-tab1pdf

模型使用的L_v(T)=2500900−2370T J/kg是根据该表趋势选取的近似直线，并非NIST原表给出的精确拟合公式。温度T以°C计。0—50°C选定核对节点与饱和蒸气压见water_properties.csv。对露点的附加检查还条件性假定总压101325 Pa、附件空气水分浓度是kg水蒸气/kg干空气。
