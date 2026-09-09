const { Document, Packer, Paragraph, TextRun, AlignmentType } = require('docx');
const fs = require('fs');

const FONT = 'Times New Roman';
const SIZE = 24; // half-points -> 12 pt, as in the colleagues' letter

function p(text, opts = {}) {
  return new Paragraph({
    alignment: opts.alignment || AlignmentType.JUSTIFIED,
    spacing: { after: opts.after === undefined ? 160 : opts.after, line: 278 },
    children: [new TextRun({ text, font: FONT, size: SIZE, bold: !!opts.bold })],
  });
}

function rich(runs, opts = {}) {
  return new Paragraph({
    alignment: opts.alignment || AlignmentType.JUSTIFIED,
    spacing: { after: opts.after === undefined ? 160 : opts.after, line: 278 },
    children: runs.map(r => new TextRun({
      text: r.t, font: FONT, size: SIZE, bold: !!r.b, italics: !!r.i,
    })),
  });
}

// Positions exactly as the authors gave them; academic degrees as listed in the DSTU
// staff directory (donstu.ru/employees), checked 2 September 2026. No courtesy titles:
// an academic signature block carries the position, not Mr./Mrs./Ms.
const AUTHORS = [
  ['Ivan I. Naumov', 'Ph.D., Head of the World-Class Research Centre "Agroengineering of the Future", corresponding author'],
  ['Maksim V. Lyashov', 'Ph.D., Software Engineer'],
  ['Anton T. Chernyaev', 'Software Engineer'],
  ['Mariya S. Kilina', 'Ph.D., Associate Professor, Department of Hydraulics, Hydropneumatic Automation and Thermal Processes'],
  ['Marina M. Zhdanova', 'Senior Lecturer, Department of Cybersecurity of Information Systems'],
  ['Elena O. Chernyaeva', 'Technician'],
  ['Marina S. Kharina', 'Software Engineer'],
  ['Angelina E. Merzlikina', 'Engineer'],
  ['Mariya N. Kulinich', 'Engineer, Research Administration Office'],
];

const body = [
  p('Agronomy Editorial Office', { alignment: AlignmentType.RIGHT, after: 0 }),
  p('MDPI, Grosspeteranlage 5, 4052 Basel, Switzerland', { alignment: AlignmentType.RIGHT, after: 240 }),
  p('COVER LETTER', { alignment: AlignmentType.CENTER, bold: true, after: 240 }),

  rich([
    { t: 'We are pleased to submit our manuscript entitled “' },
    { t: 'Multi-step stability selects sparse surrogate models for economic greenhouse climate control: an in silico study of feature-library design and actuator-pathway survival' },
    { t: '” by Ivan I. Naumov, Maksim V. Lyashov, Anton T. Chernyaev, Mariya S. Kilina, Marina M. Zhdanova, Elena O. Chernyaeva, Marina S. Kharina, Angelina E. Merzlikina, and Mariya N. Kulinich for consideration for publication in ' },
    { t: 'Agronomy', i: true },
    { t: '.' },
  ]),

  p('Protected tomato production depends on holding a productive microclimate while containing the cost of heating, supplementary lighting and CO₂ enrichment. Economic model predictive control addresses both at once, but it needs a process model, and comparing candidate models at crop scale is expensive: every candidate costs a growing season. The practical question is therefore which inexpensive, open-loop criterion should be used to select a data-driven surrogate before it is placed in the loop. Our study answers that question in silico and, in doing so, shows that the criterion the literature most often reports is the wrong one.'),

  p('The study is a controlled simulation experiment on the published GreenLight tomato greenhouse model through the GreenLight-Gym interface, driven by ERA5-derived weather for Rostov-on-Don over 60-day spring seasons. Seventy-two sparse-identification configurations were screened on the training years alone, and fifteen controllers – sparse-identification MPC variants, a neural-network MPC, two reinforcement-learning agents, an idealised planner and an agronomic heuristic – were then compared over four unseen test seasons with up to 20 identification replicates each. Every controller was scored on two axes that are reported separately and never combined into one number: the simulated seasonal economic margin and the number of steps spent outside the climate corridor.'),

  p('One-step accuracy and multi-step stability rank the candidate feature libraries in opposite directions. Adding physically motivated features lowered one-step temperature RMSE from 1.86 to 1.68 °C while raising the median 24-hour rollout error from 2.67 to 24.27 °C, and it is the library selected by the rollout criterion that then produced the best closed-loop economics: +4.32 EUR m⁻² against +3.09 for the best physics-informed variant and +2.26 for the agronomic heuristic after the heuristic itself had been tuned. The effect of adding physics is not monotone (+4.32, +0.28, +2.75), and the regression condition number does not explain it. What does track it is a controller-facing structural property: whether the direct boiler coefficient survives the sparsity threshold (55, 15, 55 %). A single-coefficient knock-in confirms the mechanism, and five of the fifteen controllers remain on the margin-violation Pareto front.'),

  p('Model selection for control-oriented surrogates is usually reported in terms of one-step prediction error, and that is the practice our results contradict: the criterion ranks candidate models in the opposite order to the one that decides the closed-loop outcome. Two further features of the work may be of particular interest to the journal. First, the comparison is protected against the asymmetries that commonly inflate such results, and the cost of that protection is reported rather than hidden: tuning the agronomic reference under the same budget the learning agents received is worth +3.49 EUR m⁻² to it, and aligning the MPC stage-cost weights with the prices used for evaluation cuts the headline library gap from +3.66 to +1.23. Second, the mechanistic reading was tested rather than asserted. We registered a prediction, ran the experiment that could refute it – deleting one bilinear feature from the richest library – and report that the prediction failed and the reading was withdrawn. The full replication package, in which every reported number carries a single frozen configuration hash and a claim-to-file map, accompanies the manuscript.'),

  p('The manuscript fits the scope of Agronomy in protected cultivation and resource-efficient greenhouse climate management, and in modelling and decision support for crop production systems. We are explicit throughout that the evidence is comparative and computational: the results establish how surrogate models for greenhouse MPC should be screened, not a field-scale economic benefit, and no agronomic recommendation is drawn that a physical greenhouse has not been asked to confirm.'),

  p('We would like this manuscript to be considered for the Special Issue “Precise Management of Crop Growth Environment in Agricultural Greenhouses”, in the section Precision and Digital Agriculture. The call names environmental control technologies, crop modelling and energy-efficient climate regulation, and the manuscript addresses all three: it screens data-driven models of the greenhouse climate for use inside an economic controller, and it measures what that choice is worth in seasonal margin and in constraint violations.'),

  p('The study is computational and involved neither human participants nor animals. We confirm that neither the manuscript nor any parts of its content are currently under consideration for publication with or published in another journal.'),

  p('All authors have approved the manuscript and agree with its submission to Agronomy.'),

  p('Respectfully,', { after: 240 }),
];

for (const [name, role] of AUTHORS) {
  body.push(rich(
    [{ t: name, b: true }, { t: ', ' + role }],
    { alignment: AlignmentType.LEFT, after: 0 },
  ));
}

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: SIZE } } } },
  sections: [{
    properties: { page: { margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 } } },
    children: body,
  }],
});

Packer.toBuffer(doc).then(buf => {
  const out = process.argv[2];
  fs.writeFileSync(out, buf);
  console.log('wrote ' + out);
});
