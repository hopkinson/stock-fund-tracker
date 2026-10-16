const { chromium } = require('playwright');
const path = require('path');

const OUTPUT_DIR = path.resolve(__dirname, '..', 'docs', 'images');
const BASE_URL = 'http://127.0.0.1:8000';

async function capture() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2 // 高清 Retina 2x 缩放
  });
  const page = await context.newPage();

  console.log('1. 打开主页面并等待渲染完成...');
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000); // 等待 ECharts 动画完成

  // 截图 1: 主看板全貌
  const overviewPath = path.join(OUTPUT_DIR, '01_dashboard_overview.png');
  await page.screenshot({ path: overviewPath, fullPage: false });
  console.log('已保存: 01_dashboard_overview.png');

  // 截图 2: 同步持仓弹窗
  await page.click('header button:has-text("同步持仓")');
  await page.waitForSelector('.fixed');
  await page.waitForTimeout(500);
  const syncPath = path.join(OUTPUT_DIR, '02_account_sync.png');
  await page.screenshot({ path: syncPath });
  console.log('已保存: 02_account_sync.png');
  await page.locator('.fixed button:has(svg.lucide-xicon)').first().click();
  await page.waitForSelector('.fixed', { state: 'detached' });
  await page.waitForTimeout(300);

  // 截图 3: AI持仓诊断与建议弹窗
  await page.click('header button:has-text("AI 分析")');
  await page.waitForSelector('.fixed');
  await page.waitForTimeout(500);
  const aiPath = path.join(OUTPUT_DIR, '03_ai_review.png');
  await page.screenshot({ path: aiPath });
  console.log('已保存: 03_ai_review.png');
  await page.locator('.fixed button:has(svg.lucide-xicon)').first().click();
  await page.waitForSelector('.fixed', { state: 'detached' });
  await page.waitForTimeout(300);

  // 截图 4: 市场风向与板块动态弹窗
  await page.click('header button:has-text("市场风向")');
  await page.waitForSelector('.fixed');
  await page.waitForTimeout(500);
  const kolPath = path.join(OUTPUT_DIR, '04_market_trends.png');
  await page.screenshot({ path: kolPath });
  console.log('已保存: 04_market_trends.png');
  await page.locator('.fixed button:has(svg.lucide-xicon)').first().click();
  await page.waitForSelector('.fixed', { state: 'detached' });
  await page.waitForTimeout(300);

  // 截图 5: 涨跌提醒弹窗
  await page.click('header button:has-text("提醒")');
  await page.waitForSelector('.fixed');
  await page.waitForTimeout(500);
  const alertPath = path.join(OUTPUT_DIR, '05_alert_settings.png');
  await page.screenshot({ path: alertPath });
  console.log('已保存: 05_alert_settings.png');
  await page.locator('.fixed button:has(svg.lucide-xicon)').first().click();
  await page.waitForSelector('.fixed', { state: 'detached' });

  await browser.close();
  console.log('所有高清截图已生成完毕！');
}

capture().catch(err => {
  console.error('截图失败:', err);
  process.exit(1);
});
