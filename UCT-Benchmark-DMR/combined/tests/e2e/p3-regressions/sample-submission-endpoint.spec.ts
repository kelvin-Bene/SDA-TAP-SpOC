import { test, expect } from '../fixtures/consoleWatcher';

/**
 * Backend regression tests for GET /api/v1/datasets/{id}/sample-submission.
 * Demo-mode gated; three quality tiers; response is JSON attachment.
 * All API calls use Bearer demo-token to match the frontend client interceptor.
 */
const DEMO_AUTH = { Authorization: 'Bearer demo-token' } as const;

test.describe('P3 Regression — Sample submission API endpoint', () => {
  const DATASET_ID = 1;

  for (const quality of ['high', 'medium', 'low'] as const) {
    test(`quality=${quality} returns 200 JSON attachment`, async ({ request }) => {
      const res = await request.get(
        `/api/v1/datasets/${DATASET_ID}/sample-submission?quality=${quality}`,
        { headers: DEMO_AUTH },
      );
      expect(res.status()).toBe(200);
      const headers = res.headers();
      expect(headers['content-type']).toMatch(/application\/json/i);
      expect(headers['content-disposition']).toContain(
        `sample_uctp_dataset${DATASET_ID}_${quality}.json`,
      );
    });

    test(`quality=${quality} body is a non-empty JSON array with UCTP shape`, async ({ request }) => {
      const res = await request.get(
        `/api/v1/datasets/${DATASET_ID}/sample-submission?quality=${quality}`,
        { headers: DEMO_AUTH },
      );
      const body = await res.json();
      expect(Array.isArray(body)).toBe(true);
      expect(body.length).toBeGreaterThan(0);
      // Sample required UCTP fields
      expect(body[0]).toHaveProperty('sourcedData');
      expect(Array.isArray(body[0].sourcedData)).toBe(true);
      expect(body[0]).toHaveProperty('epoch');
      expect(body[0]).toHaveProperty('xpos');
      expect(body[0]).toHaveProperty('ypos');
      expect(body[0]).toHaveProperty('zpos');
      expect(body[0]).toHaveProperty('xvel');
      expect(body[0]).toHaveProperty('yvel');
      expect(body[0]).toHaveProperty('zvel');
    });
  }

  test('invalid quality falls back to medium (still 200)', async ({ request }) => {
    const res = await request.get(
      `/api/v1/datasets/${DATASET_ID}/sample-submission?quality=xyz-bogus`,
      { headers: DEMO_AUTH },
    );
    expect(res.status()).toBe(200);
    // Filename uses the provided (bogus) value in the attachment header per backend behavior
    expect(res.headers()['content-disposition']).toMatch(/sample_uctp_dataset\d+_xyz-bogus\.json/);
  });

  test('unknown dataset returns 404', async ({ request }) => {
    const res = await request.get(
      '/api/v1/datasets/99999/sample-submission?quality=high',
      { headers: DEMO_AUTH },
    );
    expect(res.status()).toBe(404);
  });

  test('default quality (no query) returns 200', async ({ request }) => {
    const res = await request.get(
      `/api/v1/datasets/${DATASET_ID}/sample-submission`,
      { headers: DEMO_AUTH },
    );
    expect(res.status()).toBe(200);
  });

  test('unauthenticated request returns 401', async ({ request }) => {
    const res = await request.get(
      `/api/v1/datasets/${DATASET_ID}/sample-submission?quality=high`,
    );
    expect(res.status()).toBe(401);
  });
});
