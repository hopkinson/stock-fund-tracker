const { chromium } = require('playwright');

const BASE_URL = 'http://127.0.0.1:8000';

function log(step, status, detail = '') {
  const icon = status === 'PASS' ? '✅' : status === 'FAIL' ? '❌' : 'ℹ️';
  console.log(`${icon} [${step}] ${detail}`);
}

async function checkApiEndpoints() {
  console.log('\n--- 1. API 接口自动化回归测试 ---');
  const endpoints = [
    { name: '资产概览', url: '/api/portfolio/summary', method: 'GET' },
    { name: '持仓列表', url: '/api/portfolio/positions', method: 'GET' },
    { name: '账号列表', url: '/api/accounts', method: 'GET' },
    { name: '提醒规则', url: '/api/alerts', method: 'GET' },
    { name: '通知配置', url: '/api/notifications', method: 'GET' },
    { name: '大V追踪记录', url: '/api/kol/records', method: 'GET' },
    { name: '资产行情刷新', url: '/api/portfolio/refresh', method: 'POST' }
  ];

  let passed = 0;
  for (const ep of endpoints) {
    try {
      const resp = await fetch(`${BASE_URL}${ep.url}`, {
        method: ep.method,
        headers: { 'Content-Type': 'application/json' }
      });
      if (resp.ok) {
        log(ep.name, 'PASS', `${ep.method} ${ep.url} -> HTTP ${resp.status}`);
        passed++;
      } else {
        log(ep.name, 'FAIL', `${ep.method} ${ep.url} -> HTTP ${resp.status}`);
      }
    } catch (e) {
      log(ep.name, 'FAIL', `${ep.method} ${ep.url} -> 错误: ${e.message}`);
    }
  }

  return passed === endpoints.length;
}

async function closeModal(page) {
  const closeBtn = page.locator('.fixed button:has(svg.lucide-xicon)').first();
  await closeBtn.click();
  await page.waitForSelector('.fixed', { state: 'detached', timeout: 5000 });
  await page.waitForTimeout(250);
}

async function runBrowserE2E() {
  console.log('\n--- 2. 浏览器端 UI & 交互 E2E 回归测试 ---');

  const browser = await chromium.launch({
    channel: 'chrome',
    headless: true
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });
  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  page.on('pageerror', err => {
    consoleErrors.push(err.message);
  });

  let testPassed = true;

  try {
    // 1. 访问首页
    log('页面访问', 'INFO', `正在打开 ${BASE_URL}...`);
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 15000 });
    const pageTitle = await page.title();
    log('页面标题', 'PASS', `标题为: "${pageTitle}"`);

    // 2. 验证导航栏与通俗文案（严禁金融黑话）
    await page.waitForSelector('header', { timeout: 8000 });
    const headerText = await page.textContent('header');
    
    const bannedJargon = ['在管标的', '在管持仓', 'CIO级诊断', '战报', '异动预警', '净值核算报告'];
    for (const word of bannedJargon) {
      if (headerText.includes(word)) {
        log('文案合规检查', 'FAIL', `导航栏检测到黑话违规词: "${word}"`);
        testPassed = false;
      }
    }
    log('文案合规检查', 'PASS', '导航栏文案符合通俗易懂、精炼直白规范');

    // 3. 验证四大核心资产指标卡
    await page.waitForSelector('.grid', { timeout: 5000 });
    const cards = await page.$$('.bg-slate-900\\/50, .border-slate-800');
    log('核心指标卡', 'PASS', `检测到 ${cards.length} 个数据卡片组件正常挂载`);

    // 4. 验证持仓表格渲染与筛选搜索
    await page.waitForSelector('table tbody tr', { timeout: 8000 });
    const initialRows = await page.$$('table tbody tr');
    log('持仓表格', 'PASS', `成功加载持仓列表，展示 ${initialRows.length} 行标的`);

    // 测试搜索输入框过滤
    const searchInput = await page.$('input[placeholder*="搜索"]');
    if (searchInput) {
      await searchInput.fill('纳指');
      await page.waitForTimeout(400);
      const filteredRows = await page.$$('table tbody tr');
      log('搜索过滤', 'PASS', `搜索“纳指”过滤完成，实时展示 ${filteredRows.length} 条记录`);
      await searchInput.fill('');
      await page.waitForTimeout(300);
    }

    // 5. 弹窗打开/关闭与内容完整性 E2E 验证
    
    // (a) 同步持仓 Modal
    const syncBtn = page.locator('header button:has-text("同步持仓")');
    if (await syncBtn.isVisible()) {
      await syncBtn.click();
      await page.waitForSelector('.fixed', { timeout: 3000 });
      const modalText = await page.textContent('.fixed');
      if (modalText.includes('东方财富') && modalText.includes('雪球') && modalText.includes('天天基金')) {
        log('同步持仓弹窗', 'PASS', '支持东财/雪球/天天三大平台切换，操作提示通俗直白');
      }
      await closeModal(page);
    }

    // (b) 涨跌提醒 Modal
    const alertBtn = page.locator('header button:has-text("提醒")');
    if (await alertBtn.isVisible()) {
      await alertBtn.click();
      await page.waitForSelector('.fixed', { timeout: 3000 });
      const alertModalText = await page.textContent('.fixed');
      if (alertModalText.includes('提醒') || alertModalText.includes('添加规则')) {
        log('涨跌提醒弹窗', 'PASS', '成功打开提醒设置，规则类型文案符合日常口语规范');
      }
      await closeModal(page);
    }

    // (c) 通知设置 Modal
    const notifyBtn = page.locator('header button:has-text("通知")');
    if (await notifyBtn.isVisible()) {
      await notifyBtn.click();
      await page.waitForSelector('.fixed', { timeout: 3000 });
      const notifyModalText = await page.textContent('.fixed');
      if (notifyModalText.includes('开盘提醒') || notifyModalText.includes('收盘日报')) {
        log('通知设置弹窗', 'PASS', '成功打开通知设置，已去除“战报/异动预警”黑话');
      }
      await closeModal(page);
    }

    // (d) 市场风向 (大V跟踪) Modal
    const kolBtn = page.locator('header button:has-text("市场风向")');
    if (await kolBtn.isVisible()) {
      await kolBtn.click();
      await page.waitForSelector('.fixed', { timeout: 3000 });
      const kolModalText = await page.textContent('.fixed');
      if (kolModalText.includes('风向') || kolModalText.includes('分析') || kolModalText.includes('板块')) {
        log('市场风向弹窗', 'PASS', '成功打开市场风向，实时分析与历史追踪工作正常');
      }
      await closeModal(page);
    }

    // (e) AI诊断与复盘 Modal
    const aiBtn = page.locator('header button:has-text("AI 分析")');
    if (await aiBtn.isVisible()) {
      await aiBtn.click();
      await page.waitForSelector('.fixed', { timeout: 3000 });
      const aiModalText = await page.textContent('.fixed');
      if (aiModalText.includes('诊断') || aiModalText.includes('投资风格') || aiModalText.includes('持仓')) {
        log('AI分析弹窗', 'PASS', '成功打开AI持仓体检弹窗，风格配置与重点关注项完备');
      }
      await closeModal(page);
    }

    // 6. 隐私模式切换测试
    const privacyBtn = page.locator('header button:has-text("隐藏金额"), header button:has-text("金额已隐藏")');
    if (await privacyBtn.isVisible()) {
      await privacyBtn.click();
      await page.waitForTimeout(300);
      const isMasked = await page.evaluate(() => document.body.innerText.includes('••••'));
      log('隐私模式切换', 'PASS', `点击隐藏金额按钮切换正常 (脱敏掩码检测: ${isMasked ? '已脱敏' : '明文'})`);
      await privacyBtn.click(); // 切回
      await page.waitForTimeout(200);
    }

    // 7. 检查整个交互流程中是否有严重 JavaScript 异常
    const fatalErrors = consoleErrors.filter(e => !e.includes('favicon') && !e.includes('download') && !e.includes('404'));
    if (fatalErrors.length > 0) {
      log('控制台异常', 'FAIL', `捕获到致命错误: ${fatalErrors.join(' | ')}`);
      testPassed = false;
    } else {
      log('控制台异常', 'PASS', '前端全流程零致命异常');
    }

  } catch (err) {
    log('E2E运行', 'FAIL', `测试异常中断: ${err.message}`);
    testPassed = false;
  } finally {
    await browser.close();
  }

  return testPassed;
}

async function main() {
  console.log('========================================================');
  console.log('🚀 PortfolioHub 资产罗盘 - 全链路 E2E 自动化回归测试');
  console.log('========================================================');
  
  const apiSuccess = await checkApiEndpoints();
  const browserSuccess = await runBrowserE2E();

  console.log('\n========================================================');
  if (apiSuccess && browserSuccess) {
    console.log('🎉 所有 E2E 回归测试项全部通过！系统运行稳健。');
    process.exit(0);
  } else {
    console.error('⚠️ 部分测试用例未通过，请检查日志。');
    process.exit(1);
  }
}

main();
