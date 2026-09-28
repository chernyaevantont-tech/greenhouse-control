const { Document, Packer, Paragraph, TextRun, HeadingLevel } = require('docx');
const fs = require('fs');
const path = require('path');

const metadata = JSON.parse(fs.readFileSync(path.join(__dirname, 'authors.json'), 'utf8'));
const names = metadata.authors.map(a => a.name);
const corresponding = metadata.authors.find(a => a.corresponding);
const title = 'Multi-step stability selects sparse surrogate models for economic greenhouse climate control: an in silico study of feature-library design and actuator-pathway survival';
const study = 'Our controlled simulation study uses the published GreenLight tomato greenhouse model driven by ERA5-derived weather. We screen 72 sparse-identification configurations and compare 15 controllers over four test seasons, reporting simulated seasonal margin and climate-corridor violations separately. Among first-order, undenoised configurations under sparse estimators, one-step accuracy and multi-step rollout stability rank the feature libraries in opposite directions. Multi-step stability selects the raw-library surrogate with the highest mean seasonal margin (+4.32 EUR m⁻²), compared with +3.09 for the best physics-informed variant and +2.26 for the tuned agronomic heuristic.';
const contribution = 'The manuscript addresses model selection for economic greenhouse climate control and quantifies how reference-controller tuning and consistent economic weights affect the comparison. It also examines whether the direct boiler coefficient survives sparse identification. The evidence is computational and comparative; the manuscript explicitly reports limitations and does not claim validation in a physical greenhouse.';
const p = (text, opts = {}) => new Paragraph({
  ...opts,
  spacing: { after: 120, line: 252 },
  children: text.split('\n').map((line, i) => new TextRun({ text: line, break: i ? 1 : 0 })),
});

const body = [
  p('Cover letter', { heading: HeadingLevel.TITLE }),
  p('Dear Dr. Xu and Editors of Agronomy,'),
  p(`Please consider our research article, “${title}”, for the Special Issue “Intelligent Control of Greenhouse Climate”, in the section Precision and Digital Agriculture.`),
  p('Authors: ' + names.slice(0, -1).join(', ') + ', and ' + names.at(-1) + '.'),
  p(study),
  p(contribution),
  p('Analysis code is available at https://doi.org/10.5281/zenodo.22939740. The complete replication tree, including per-run results and the claim-to-file map, is publicly linked in the manuscript’s Data Availability Statement.'),
  p('We confirm that neither the manuscript nor any parts of its content are currently under consideration for publication with or published in another journal.'),
  p('All authors have approved the manuscript and agree with its submission to Agronomy.'),
  p('Sincerely,'),
  p(`${corresponding.name}\nCorresponding author, on behalf of all authors\nDon State Technical University, Rostov-on-Don, Russia\n${corresponding.email}`),
];

const doc = new Document({
  creator: corresponding.name,
  title: 'Cover letter for Agronomy submission',
  styles: {
    default: { document: { run: { font: 'Times New Roman', size: 22, color: '000000' } } },
    paragraphStyles: [{ id: 'Title', name: 'Title', basedOn: 'Normal', next: 'Normal',
      run: { font: 'Times New Roman', size: 26, bold: true, color: '000000' },
      paragraph: { keepNext: true, spacing: { after: 160 } } }],
  },
  sections: [{ properties: { page: {
    size: { width: 11906, height: 16838 },
    margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 },
  } }, children: body }],
});

Packer.toBuffer(doc).then(buffer => {
  const out = process.argv[2] || path.join(__dirname, 'cover_letter.docx');
  fs.writeFileSync(out, buffer);
  console.log('wrote ' + out);
});
