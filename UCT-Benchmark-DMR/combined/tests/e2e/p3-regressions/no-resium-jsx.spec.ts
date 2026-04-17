import { test, expect } from '../fixtures/consoleWatcher';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Static-analysis regression guard for commit fed4677 (resium bypass).
 * The Cesium integration was rewritten to mount the Viewer directly via useEffect,
 * avoiding resium's React wrapper (which was causing double-mount and entity errors).
 *
 * If resium JSX returns, Cesium may re-break. This test walks the frontend Cesium folder
 * and fails if any *.tsx file contains `from 'resium'` or resium JSX tags.
 */
test.describe('P3 Regression — No resium JSX imports', () => {
  test('Cesium folder contains no resium imports or JSX tags', async () => {
    const cesiumDir = path.resolve(
      __dirname,
      '..',
      '..',
      '..',
      'frontend',
      'src',
      'components',
      'cesium',
    );
    const files = fs.existsSync(cesiumDir)
      ? fs
          .readdirSync(cesiumDir)
          .filter((f) => /\.(ts|tsx)$/.test(f))
          .map((f) => path.join(cesiumDir, f))
      : [];
    expect(files.length, `Expected Cesium source files in ${cesiumDir}`).toBeGreaterThan(0);

    const offenders: string[] = [];
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf8');
      if (/from\s+['"]resium['"]/.test(content)) {
        offenders.push(`${file}: imports from 'resium'`);
      }
      if (/<Viewer\b/.test(content) && /from\s+['"]resium['"]/.test(content)) {
        offenders.push(`${file}: uses <Viewer> JSX from resium`);
      }
      if (/<Entity\b/.test(content) && /from\s+['"]resium['"]/.test(content)) {
        offenders.push(`${file}: uses <Entity> JSX from resium`);
      }
    }
    expect(
      offenders,
      'Resium imports/JSX must not return (see commit fed4677)',
    ).toEqual([]);
  });
});
