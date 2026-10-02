async (page) => {
  const box = await page.getByRole('img', { name: 'Vista de la cámara', exact: true }).boundingBox();
  await page.getByRole('button', { name: 'Dibujar de nuevo', exact: true }).click();
  await page.mouse.click(box.x + box.width * 0.2, box.y + box.height * 0.3);
  await page.mouse.click(box.x + box.width * 0.8, box.y + box.height * 0.7);
  const response = page.waitForResponse(r => r.request().method() === 'PATCH' && r.url().includes('/rules/line/1'));
  await page.getByRole('button', { name: 'Guardar en la cámara', exact: true }).click();
  const saved = await response;
  console.log(JSON.stringify({ test: 'dibujar y guardar por UI', status: saved.status(), result: await saved.json() }));
  await page.screenshot({ path: 'output/playwright/regla-guardada.png' });
}
