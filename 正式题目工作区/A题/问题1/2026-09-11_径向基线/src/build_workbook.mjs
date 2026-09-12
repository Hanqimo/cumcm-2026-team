import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
const root=process.env.Q1_ROOT;
if(!root) throw new Error('Set Q1_ROOT to the run directory');
const payload=JSON.parse(await fs.readFile(path.join(root,'results/workbook_payload.json'),'utf8'));
const wb=Workbook.create();
const log=[];
for(const [name,values] of Object.entries(payload)){
 const s=wb.worksheets.add(name);
 s.getRange('A1:V1801').values=values;
 s.getRange('A1:V1801').format.font={name:'Arial',size:11};
 s.getRange('A1:V1801').format.rowHeight=20;
 s.getRange('A1:A1801').format.columnWidth=28;
 s.getRange('B1:V1801').format.columnWidth=12;
 s.getRange('A1:V1').format.fill='#E8EDF2';
 s.getRange('A1:V1').format.font={name:'Arial',size:11,bold:true,color:'#172B4D'};
 s.getRange('A1:V1').format.rowHeight=32;
 s.getRange('A1:V1').format.wrapText=true;
 s.getRange('A1:V1801').format.verticalAlignment='center';
 s.getRange('A2:A1801').setNumberFormat('0');
 s.getRange('B1:V1').setNumberFormat('0.0');
 s.getRange('B2:V1801').setNumberFormat('0.0000');
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(1);
 log.push(await wb.inspect({kind:'region',sheetId:name,range:'A1:G8',maxChars:2400}));
 log.push(await wb.inspect({kind:'region',sheetId:name,range:'R1797:V1801',maxChars:1200}));
 for(const [key,range] of [['early','A1:G8'],['late','Q1795:V1801']]){
  const blob=await wb.render({sheetName:name,range,scale:1.5,format:'png'});
  await fs.writeFile(path.join(root,`verification/xlsx_${name}_${key}.png`),new Uint8Array(await blob.arrayBuffer()));
 }
}
log.push(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},summary:'Final error scan'}));
await fs.writeFile(path.join(root,'verification/workbook_inspect.json'),JSON.stringify(log,null,2));
const file=await SpreadsheetFile.exportXlsx(wb);await file.save(path.join(root,'results/result1.xlsx'));
console.log('Exported two worksheets, 1800 times x 21 radii per field.');
