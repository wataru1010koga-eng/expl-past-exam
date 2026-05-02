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
  r6: { label: '令和6年度（2024年）', shortLabel: 'R6', hasExplanations: false },
  r5: { label: '令和5年度（2023年）', shortLabel: 'R5', hasExplanations: false },
  r4: { label: '令和4年度（2022年）', shortLabel: 'R4', hasExplanations: false },
  r3: { label: '令和3年度（2021年）', shortLabel: 'R3', hasExplanations: false },
};

function parseCSVLine(line: string): string[] {
  const fields: string[] = [];
  let current = '';
  let inQuote = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuote && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuote = !inQuote;
      }
    } else if (char === ',' && !inQuote) {
      fields.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  fields.push(current);
  return fields;
}

export function getQuestions(yearKey: string): Question[] {
  const csvPath = join(process.cwd(), 'content', yearKey, `${yearKey}_questions.csv`);
  const content = readFileSync(csvPath, 'utf-8').replace(/^﻿/, '');

  const lines = content.trim().split('\n');
  return lines
    .slice(1)
    .filter(line => line.trim())
    .map(line => {
      const fields = parseCSVLine(line);
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
