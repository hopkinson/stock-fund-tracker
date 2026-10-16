<template>
  <div class="min-h-screen flex flex-col bg-[#0b0f17] text-slate-100 relative selection:bg-indigo-500 selection:text-white">
    <!-- 顶部微环境光晕 (非廉价大光圈，仅轻微氛围深度) -->
    <div class="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-48 bg-gradient-to-b from-indigo-500/5 via-slate-900/10 to-transparent pointer-events-none blur-3xl"></div>

    <!-- 顶部导航 -->
    <Navbar 
      :refreshing="refreshing"
      :privacy-mode="isPrivacyMode"
      :last-updated="lastUpdatedTime"
      @refresh="loadData(true)"
      @toggle-privacy="togglePrivacy"
      @open-accounts="showAccountModal = true"
      @open-alerts="showAlertModal = true"
      @open-notify="showNotifyModal = true"
      @open-ai="showAIModal = true"
      @open-kol="showKOLModal = true"
    />

    <!-- 主工作区 -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-3.5 sm:px-6 lg:px-8 py-5 sm:py-6 space-y-5 sm:space-y-6 relative z-10">
      <!-- 资产概览大卡片 -->
      <OverviewCards 
        :summary="summary" 
        :privacy-mode="isPrivacyMode"
      />

      <!-- 资产分布图表 (平台分布 + 类别分布，结合精细进度条) -->
      <DistributionChart 
        :platformData="distributionByPlatform"
        :typeData="distributionByType"
        :privacy-mode="isPrivacyMode"
      />

      <!-- 持仓列表与明细表格 (排序、分类、搜索、平台统计、一键复制) -->
      <PositionTable 
        :positions="positions"
        :privacy-mode="isPrivacyMode"
        @delete-pos="handleDeletePos"
      />
    </main>

    <!-- 页脚 -->
    <footer class="border-t border-slate-800/60 py-5 text-center text-xs text-slate-500 relative z-10">
      <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
        <p>PortfolioHub 资产看板 · 个人多账户股票与基金看板</p>
        <p class="text-slate-600 text-[11px]">行情数据源由东方财富、雪球基金、天天基金提供</p>
      </div>
    </footer>

    <!-- 弹窗集 (纯自动化同步体系) -->
    <AccountModal 
      :visible="showAccountModal"
      @close="showAccountModal = false"
      @refresh="loadData"
    />

    <AlertModal 
      :visible="showAlertModal"
      :positions="positions"
      @close="showAlertModal = false"
    />

    <NotifyModal 
      :visible="showNotifyModal"
      @close="showNotifyModal = false"
    />

    <AIReviewModal 
      :visible="showAIModal"
      :positions="positions"
      :summary="summary"
      @close="showAIModal = false"
    />

    <KOLTrackerModal 
      :visible="showKOLModal"
      @close="showKOLModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import Navbar from './components/Navbar.vue'
import OverviewCards from './components/OverviewCards.vue'
import DistributionChart from './components/DistributionChart.vue'
import PositionTable from './components/PositionTable.vue'
import AccountModal from './components/AccountModal.vue'
import AlertModal from './components/AlertModal.vue'
import NotifyModal from './components/NotifyModal.vue'
import AIReviewModal from './components/AIReviewModal.vue'
import KOLTrackerModal from './components/KOLTrackerModal.vue'

import { getPortfolioSummary, getPositions, deletePosition, refreshQuotes } from './api'

const refreshing = ref(false)
const lastUpdatedTime = ref('')
const isPrivacyMode = ref(false)
const showKOLModal = ref(false)

const summary = ref({
  total_asset: 0,
  total_cost: 0,
  today_profit: 0,
  today_profit_rate: 0,
  total_profit: 0,
  total_profit_rate: 0,
  position_count: 0
})
const distributionByPlatform = ref({})
const distributionByType = ref({})
const positions = ref([])

// 弹窗状态
const showAccountModal = ref(false)
const showAlertModal = ref(false)
const showNotifyModal = ref(false)
const showAIModal = ref(false)

let pollTimer = null

const togglePrivacy = () => {
  isPrivacyMode.value = !isPrivacyMode.value
  try {
    localStorage.setItem('portfolio_privacy_mode', isPrivacyMode.value ? 'true' : 'false')
  } catch (e) {
    // 忽略某些无痕模式 localstorage 异常
  }
}

const updateTimeStr = () => {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  lastUpdatedTime.value = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}

const loadData = async (manual = false) => {
  if (manual) refreshing.value = true
  try {
    if (manual) {
      await refreshQuotes()
    }
    const [summaryRes, posRes] = await Promise.all([
      getPortfolioSummary(),
      getPositions()
    ])
    summary.value = summaryRes.data.summary || {}
    distributionByPlatform.value = summaryRes.data.distribution_by_platform || {}
    distributionByType.value = summaryRes.data.distribution_by_type || {}
    positions.value = posRes.data || []
    updateTimeStr()
  } catch (e) {
    console.error('加载资产数据失败:', e)
  } finally {
    if (manual) refreshing.value = false
  }
}

const handleDeletePos = async (posId) => {
  if (!confirm('确定要删除这条持仓吗？')) return
  try {
    await deletePosition(posId)
    await loadData()
  } catch (e) {
    alert('删除失败: ' + e.message)
  }
}

onMounted(() => {
  try {
    isPrivacyMode.value = localStorage.getItem('portfolio_privacy_mode') === 'true'
  } catch (e) {
    isPrivacyMode.value = false
  }

  loadData()
  // 盘中静默每 25 秒刷新一次行情
  pollTimer = setInterval(() => {
    loadData(false)
  }, 25000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
