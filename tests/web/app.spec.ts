import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

import { expect, test, type Page } from '@playwright/test';

const require = createRequire(import.meta.url);
const AXE_SOURCE = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf-8');

async function openFirstSet(page: Page): Promise<void> {
  await page.goto('/');
  const navItem = page.locator('.nav-item').first();
  await expect(navItem).toBeVisible();
  await navItem.click();
}

test('de app laadt en toont de navigatie', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Oefenomgeving' })).toBeVisible();
  await expect(page.locator('.nav-item').first()).toBeVisible();
});

test('een correct antwoord wordt goedgekeurd', async ({ page }) => {
  await openFirstSet(page);

  const firstActivity = page.locator('.activity').first();
  const input = firstActivity.locator('.prompt__input').first();
  await expect(input).toBeVisible();

  // De fixture gebruikt voorspelbare antwoorden van de vorm answer-a01p1.
  await input.fill('answer-a01p1');
  await firstActivity.getByRole('button', { name: 'Nakijken' }).first().click();

  await expect(firstActivity.locator('.prompt__feedback').first()).toHaveClass(/is-correct/);
});

test('een fout antwoord krijgt gerichte feedback zonder het antwoord te tonen', async ({ page }) => {
  await openFirstSet(page);

  const firstActivity = page.locator('.activity').first();
  const input = firstActivity.locator('.prompt__input').first();
  await input.fill('duidelijk-verkeerd');
  await firstActivity.getByRole('button', { name: 'Nakijken' }).first().click();

  const feedback = firstActivity.locator('.prompt__feedback').first();
  await expect(feedback).toHaveClass(/is-incorrect/);
  await expect(feedback).not.toContainText('answer-a01p1');
});

test('het modelantwoord verschijnt pas na het maximum aantal pogingen', async ({ page }) => {
  await openFirstSet(page);

  const firstActivity = page.locator('.activity').first();
  const input = firstActivity.locator('.prompt__input').first();
  const check = firstActivity.getByRole('button', { name: 'Nakijken' }).first();
  const feedback = firstActivity.locator('.prompt__feedback').first();

  for (let attempt = 1; attempt <= 2; attempt += 1) {
    await input.fill(`fout-${attempt}`);
    await check.click();
    await expect(feedback).not.toContainText('Modelantwoord');
  }

  await input.fill('fout-3');
  await check.click();
  await expect(feedback).toContainText('Modelantwoord');
});

test('leerlingmodus verbergt de antwoorden, leerkrachtmodus toont ze', async ({ page }) => {
  await openFirstSet(page);

  const answerBox = page.locator('.prompt__answer').first();
  await expect(answerBox).toBeHidden();

  await page.getByRole('button', { name: 'Leerkracht' }).click();
  await expect(page.locator('.prompt__answer').first()).toBeVisible();
});

test('hints zijn progressief en verklappen het antwoord niet', async ({ page }) => {
  await openFirstSet(page);

  const firstActivity = page.locator('.activity').first();
  const hintButton = firstActivity.getByRole('button', { name: 'Hint' }).first();
  const hintBox = firstActivity.locator('.prompt__hint').first();

  await hintButton.click();
  await expect(hintBox).toBeVisible();
  const firstHint = await hintBox.textContent();

  await hintButton.click();
  await expect(hintBox).not.toHaveText(firstHint ?? '');
  await expect(hintBox).not.toContainText('answer-a01p1');
});

test('voortgang blijft bewaard na herladen', async ({ page }) => {
  await openFirstSet(page);

  const firstActivity = page.locator('.activity').first();
  await firstActivity.locator('.prompt__input').first().fill('answer-a01p1');
  await firstActivity.getByRole('button', { name: 'Nakijken' }).first().click();
  await expect(firstActivity.locator('.prompt__feedback').first()).toHaveClass(/is-correct/);

  await page.reload();
  await page.locator('.nav-item').first().click();
  await expect(page.locator('.activity').first().locator('.prompt__feedback').first()).toHaveClass(
    /is-correct/,
  );
});

test('de oefening is met het toetsenbord te bedienen', async ({ page }) => {
  await openFirstSet(page);

  const input = page.locator('.activity').first().locator('.prompt__input').first();
  await input.focus();
  await expect(input).toBeFocused();

  await page.keyboard.type('answer-a01p1');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Nakijken' }).first()).toBeFocused();

  await page.keyboard.press('Enter');
  await expect(page.locator('.prompt__feedback').first()).toHaveClass(/is-correct/);
});

test('axe-core vindt geen toegankelijkheidsschendingen', async ({ page }) => {
  await openFirstSet(page);
  await page.addScriptTag({ content: AXE_SOURCE });

  const results = await page.evaluate(async () => {
    // @ts-expect-error axe wordt op runtime ingespoten
    return await window.axe.run(document, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
    });
  });

  const violations = (results as { violations: { id: string; nodes: unknown[] }[] }).violations;
  const summary = violations.map((v) => `${v.id} (${v.nodes.length}x)`).join(', ');
  expect(summary).toBe('');
});
