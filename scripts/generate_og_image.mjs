import sharp from 'sharp';
import { readFileSync } from 'fs';

const svg = readFileSync('./public/og-image.svg');
await sharp(Buffer.from(svg)).png().toFile('./public/og-image.png');
console.log('og-image.png generated');
