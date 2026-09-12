import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.Q1_ROOT;
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(`${root}/results/result1.xlsx`));
const png=await wb.render({sheetName:'水分浓度',range:'Q1:V8',scale:1.25,format:'png'});
await fs.writeFile(`${root}/verification/result_水分浓度_reimport.png`,new Uint8Array(await png.arrayBuffer()));
