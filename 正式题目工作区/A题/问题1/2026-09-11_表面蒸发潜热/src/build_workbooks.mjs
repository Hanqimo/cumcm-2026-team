import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.Q1_ROOT;if(!root)throw new Error('Set Q1_ROOT');
const p=JSON.parse(await fs.readFile(path.join(root,'results/workbook_payload.json'),'utf8'));
const m=p.metadata, logs=[];
function style(sheet,range){const r=sheet.getRange(range);r.format.font={name:'Arial',size:11};r.format.rowHeight=22;r.format.columnWidth=13;}
async function preview(wb,sheet,range,name){const image=await wb.render({sheetName:sheet,range,scale:1.25,format:'png'});await fs.writeFile(path.join(root,'verification',name),new Uint8Array(await image.arrayBuffer()));}
const wb=Workbook.create();
for(const name of ['温度','水分浓度']){
 const s=wb.worksheets.add(name);s.getRange('A1:V1801').values=p[name];style(s,'A1:V1801');
 s.getRange('A1:A1801').format.columnWidth=28;s.getRange('A1:V1').format.fill='#E8EDF2';s.getRange('A1:V1').format.font.bold=true;s.getRange('A1:V1').format.rowHeight=32;
 s.getRange('B1:V1').setNumberFormat('0.0');s.getRange('B2:V1801').setNumberFormat('0.0000');s.getRange('A2:A1801').setNumberFormat('0');s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(1);
 logs.push(await wb.inspect({kind:'region',sheetId:name,range:'Q1:V8',maxChars:1800}));
 await preview(wb,name,'Q1:V8',`result_${name}.png`);
}
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'results/result1.xlsx'));
const comp=Workbook.create(),front=comp.worksheets.add('对比概览'),data=comp.worksheets.add('时间序列');
data.getRange('A1:M1802').values=p.comparison_series;style(data,'A1:M1802');data.getRange('A1:M1').format.fill='#E8EDF2';data.getRange('A1:M1').format.font.bold=true;data.getRange('A1:M1').format.wrapText=true;data.getRange('A1:M1').format.rowHeight=48;data.getRange('B2:J1802').setNumberFormat('0.0000');data.getRange('K2:K1802').setNumberFormat('0.00000000');data.getRange('L2:M1802').setNumberFormat('0.0000');
data.getRange('F2:F1802').formulas=Array.from({length:1801},(_,i)=>[`=D${i+2}-E${i+2}`]);
data.getRange('I2:I1802').formulas=Array.from({length:1801},(_,i)=>[`=G${i+2}-H${i+2}`]);data.freezePanes.freezeRows(1);data.freezePanes.freezeColumns(1);
const plot=[['时间/min','无潜热轴心','有潜热轴心','无潜热表面','有潜热表面']];for(let i=0;i<=1800;i+=60){const v=p.comparison_series[i+1];plot.push([i/60,...v.slice(1,5)]);}data.getRange('O1:S32').values=plot;style(data,'O1:S32');data.getRange('P2:S32').setNumberFormat('0.0000');
style(front,'A1:E25');front.getRange('A1:A25').format.columnWidth=32;front.getRange('B1:D25').format.columnWidth=17;
front.getRange('A1').values=[['表面蒸发潜热的影响']];front.getRange('A1').format.font={name:'Arial',size:15,bold:true};front.getRange('A2').values=[['第一问，0—1800 s']];
front.getRange('A4').values=[['1800秒时的温度（°C）']];front.getRange('A5:D8').values=[['位置','无潜热','有潜热','降低'],['轴心',m.T_no_latent_at1800[0],m.T_at1800[0],null],['表面',m.T_no_latent_at1800[4],m.T_at1800[4],null],['体积平均',m.mean_T0_at1800,m.mean_T_at1800,null]];
front.getRange('D6:D8').formulas=[['=B6-C6'],['=B7-C7'],['=B8-C8']];front.getRange('A5:D5').format.fill='#E8EDF2';front.getRange('A5:D5').format.font.bold=true;front.getRange('B6:D8').setNumberFormat('0.0000');
front.getRange('A10:B15').values=[['全输出最大温差（°C）',m.max_temperature_drop_C],['最低温度（°C）',m.temperature_stats.min_T],['最低温度时刻（s）',m.temperature_stats.min_time_s],['表面干基含水率（kg/kg）',m.C_at1800[4]],['两模型水分解最大差',0],['新增假设：干密度（kg/m³）',m.rho_d_kg_m3]];front.getRange('B10:B15').setNumberFormat('0.0000');
front.getRange('A17:B21').values=[['解释范围','保持原有效水分边界，仅加入表面汽化耗热。'],['物理局限','按通常空气含湿量解释，低温结果与仍持续蒸发存在冲突。'],['潜热（J/kg）','2500900−2370T，T单位为°C。'],['物性来源','https://www.nist.gov/document/nistir5078-tab1pdf'],['数值检查','完整输出加密差通过门槛；四位小数末位仍有不确定性。']];front.getRange('B17:B21').format.wrapText=true;front.getRange('A17:B21').format.rowHeight=72;front.getRange('B17:B21').format.columnWidth=29;
const chart=front.charts.add('line',data.getRange('O1:S32'));chart.title='温度随时间的变化';chart.titleTextStyle.typeface='Arial';chart.titleTextStyle.fontSize=14;chart.setPosition('F4','P24');chart.legend={position:'bottom',textStyle:{typeface:'Arial',fontSize:11}};chart.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:10}};chart.xAxis.title.text='时间 / min';chart.yAxis={numberFormatCode:'0',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:10}};chart.yAxis.title.text='温度 / °C';
logs.push(await comp.inspect({kind:'region',sheetId:'对比概览',range:'A4:D15',maxChars:2200}));logs.push(await comp.inspect({kind:'region',sheetId:'时间序列',range:'A1800:M1802',maxChars:2200}));
logs.push(await comp.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#SPILL!',options:{useRegex:true,maxResults:20},summary:'Formula errors'}));
await preview(comp,'对比概览','A1:P24','comparison_summary.png');await preview(comp,'时间序列','A1798:M1802','comparison_data.png');
await (await SpreadsheetFile.exportXlsx(comp)).save(path.join(root,'results/模型对比.xlsx'));
await fs.writeFile(path.join(root,'verification/workbook_inspect.json'),JSON.stringify(logs,null,2));
console.log('Exported result1.xlsx and 模型对比.xlsx');
