import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const workbook=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(root,'inputs/result2_template.xlsx')));
if(process.argv.includes('--preview-template')){
 const p=await workbook.render({sheetName:'温度',range:'A1:F5',scale:1.5,format:'png'});
 await fs.writeFile(path.join(root,'verification/template_preview.png'),new Uint8Array(await p.arrayBuffer()));
 console.log((await workbook.inspect({kind:'workbook,sheet,table',maxChars:2500,tableMaxRows:5,tableMaxCols:6})).ndjson);
 process.exit(0);
}
const p=JSON.parse(await fs.readFile(path.join(root,'results/workbook_payload.json'),'utf8'));
const logs=[];
for(const name of ['温度','水分浓度']){
 const s=workbook.worksheets.getItem(name),matrix=p[name];
 s.getRange('A1:V10801').values=matrix;
 s.getRange('A1:V10801').format.font={name:'Arial',size:11};
 s.getRange('A1:V10801').format.rowHeight=21;
 s.getRange('B1:V10801').format.columnWidth=12;
 s.getRange('A1:A10801').format.columnWidth=30;
 s.getRange('A1:V1').format.fill='#E8EDF2';s.getRange('A1:V1').format.font.bold=true;s.getRange('A1:V1').format.rowHeight=28;
 s.getRange('B1:V1').setNumberFormat('0.0');s.getRange('A2:A10801').setNumberFormat('0');s.getRange('B2:V10801').setNumberFormat('0.0000');
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(1);
 logs.push(await workbook.inspect({kind:'region',sheetId:name,range:'A1:F6',maxChars:1800}));
 logs.push(await workbook.inspect({kind:'region',sheetId:name,range:'Q10798:V10801',maxChars:1800}));
 for(const [range,suffix] of [['A1:F6','start'],['Q10798:V10801','end']]){
  const png=await workbook.render({sheetName:name,range,scale:1.4,format:'png'});
  await fs.writeFile(path.join(root,`verification/workbook_${name}_${suffix}.png`),new Uint8Array(await png.arrayBuffer()));
 }
}
logs.push(await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!',options:{useRegex:true,maxResults:20},summary:'Final workbook error scan'}));
await (await SpreadsheetFile.exportXlsx(workbook)).save(path.join(root,'results/result2.xlsx'));
await fs.writeFile(path.join(root,'verification/workbook_inspect.json'),JSON.stringify(logs,null,2));
console.log('Exported result2.xlsx with 10800 by 21 values on each of two sheets.');
