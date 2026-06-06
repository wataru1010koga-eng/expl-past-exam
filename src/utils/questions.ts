import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

export interface Question {
  year: number;
  number: number;
  question: string;
  answer: number;
  choices: string[];
}

export interface ExplanationSections {
  answer: string;
  explanation: string;
  reference: string;
}

export interface QuestionWithExplanation extends Question {
  explanationSections: ExplanationSections | null;
}

export const YEAR_INFO: Record<string, { label: string; shortLabel: string; hasExplanations: boolean }> = {
  r7: { label: '令和7年度（2025年）', shortLabel: 'R7', hasExplanations: true },
  r6: { label: '令和6年度（2024年）', shortLabel: 'R6', hasExplanations: true },
  r5: { label: '令和5年度（2023年）', shortLabel: 'R5', hasExplanations: true },
  r4: { label: '令和4年度（2022年）', shortLabel: 'R4', hasExplanations: true },
  r3: { label: '令和3年度（2021年）', shortLabel: 'R3', hasExplanations: true },
};

function parseCSVContent(content: string): string[][] {
  const rows: string[][] = [];
  let pos = 0;

  while (pos < content.length) {
    const row: string[] = [];

    while (pos < content.length) {
      let field = '';
      if (content[pos] === '"') {
        pos++;
        while (pos < content.length) {
          if (content[pos] === '"') {
            if (pos + 1 < content.length && content[pos + 1] === '"') {
              field += '"';
              pos += 2;
            } else {
              pos++;
              break;
            }
          } else {
            field += content[pos++];
          }
        }
      } else {
        while (pos < content.length && content[pos] !== ',' && content[pos] !== '\n' && content[pos] !== '\r') {
          field += content[pos++];
        }
      }
      row.push(field);

      if (pos < content.length && content[pos] === ',') {
        pos++;
      } else {
        break;
      }
    }

    if (pos < content.length && content[pos] === '\r') pos++;
    if (pos < content.length && content[pos] === '\n') pos++;

    if (row.some(f => f.trim())) rows.push(row);
  }

  return rows;
}

export function getQuestions(yearKey: string): Question[] {
  const csvPath = join(process.cwd(), 'content', yearKey, `${yearKey}_questions.csv`);
  const content = readFileSync(csvPath, 'utf-8').replace(/^﻿/, '');

  const rows = parseCSVContent(content);
  return rows
    .slice(1)
    .filter(fields => fields.some(f => f.trim()))
    .map(fields => {
      const [yearStr, numberStr, question, answerStr, ...choices] = fields;
      return {
        year: parseInt(yearStr),
        number: parseInt(numberStr),
        question,
        answer: parseInt(answerStr),
        choices: choices.filter(c => c.trim() !== ''),
      };
    });
}

export function getQuestionWithExplanation(yearKey: string, number: number): QuestionWithExplanation | null {
  const questions = getQuestions(yearKey);
  const question = questions.find(q => q.number === number);
  if (!question) return null;

  const numStr = String(number).padStart(2, '0');
  const mdPath = join(process.cwd(), 'content', yearKey, `${yearKey}_III_${numStr}.md`);

  if (!existsSync(mdPath)) {
    return { ...question, explanationSections: null };
  }

  const content = readFileSync(mdPath, 'utf-8');
  const bodyMatch = content.match(/^---[\s\S]*?---\n([\s\S]*)$/);
  const body = bodyMatch ? bodyMatch[1].trim() : content;

  const answerMatch = body.match(/【正答】([^\n]*)/);
  const explanationMatch = body.match(/【解説】\n([\s\S]*?)(?=\n?【参考】|$)/);
  const referenceMatch = body.match(/【参考】\n([\s\S]*?)$/);

  return {
    ...question,
    explanationSections: {
      answer: answerMatch?.[1].trim() ?? '',
      explanation: explanationMatch?.[1].trim() ?? '',
      reference: referenceMatch?.[1].trim() ?? '',
    },
  };
}
