<template>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <!-- 1. 按平台资产分布 -->
    <div class="fin-glow-card bg-[#0e1626]/90 border border-slate-800/80 hover:border-slate-700/90 rounded-2xl p-5 flex flex-col justify-between">
      <div class="flex items-center justify-between pb-3 border-b border-slate-800/60 mb-3">
        <div class="flex items-center space-x-2">
          <div class="w-2 h-2 rounded-full bg-indigo-500"></div>
          <h3 class="text-sm font-semibold text-slate-200">资金多平台分布</h3>
        </div>
        <div class="text-xs text-slate-400 flex items-center space-x-1.5">
          <span>平台合计:</span>
          <span class="font-semibold text-slate-200 num-font">
            ¥{{ privacyMode ? '••••••' : formatMoney(platformTotal) }}
          </span>
        </div>
      </div>

      <div class="flex flex-col sm:flex-row items-center gap-4 flex-1">
        <!-- 环形图 -->
        <div class="w-full sm:w-44 h-44 shrink-0 flex items-center justify-center relative">
          <div ref="platformChartRef" class="w-full h-full"></div>
          <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
            <span class="text-[10px] text-slate-400 font-medium">账户分布</span>
            <span class="text-xs font-bold text-slate-200 mt-0.5">{{ platformList.length }} 个平台</span>
          </div>
        </div>

        <!-- 详细结构清单与进度条 -->
        <div class="flex-1 w-full space-y-3">
          <div 
            v-for="item in platformList" 
            :key="item.key"
            class="group p-2 rounded-xl bg-slate-900/60 hover:bg-slate-800/60 border border-slate-800/50 transition-all"
          >
            <div class="flex items-center justify-between text-xs mb-1.5">
              <div class="flex items-center space-x-2">
                <span class="w-2 h-2 rounded-full shrink-0" :style="{ backgroundColor: item.color }"></span>
                <span class="font-medium text-slate-200">{{ item.name }}</span>
              </div>
              <div class="flex items-center space-x-2">
                <span class="font-semibold text-slate-200 num-font">
                  ¥{{ privacyMode ? '••••••' : formatMoney(item.value) }}
                </span>
                <span 
                  class="text-[11px] font-bold num-font px-1.5 py-0.2 rounded"
                  :style="{ color: item.color, backgroundColor: `${item.color}15` }"
                >
                  {{ item.percentage }}%
                </span>
              </div>
            </div>
            <!-- 视觉进度条 -->
            <div class="w-full h-1.5 bg-slate-800/80 rounded-full overflow-hidden">
              <div 
                class="h-full rounded-full transition-all duration-500"
                :style="{ width: `${item.percentage}%`, backgroundColor: item.color }"
              ></div>
            </div>
          </div>

          <div v-if="platformList.length === 0" class="py-6 text-center text-xs text-slate-400">
            暂无持仓资产分布
          </div>
        </div>
      </div>
    </div>

    <!-- 2. 按资产类别分布 -->
    <div class="fin-glow-card bg-[#0e1626]/90 border border-slate-800/80 hover:border-slate-700/90 rounded-2xl p-5 flex flex-col justify-between">
      <div class="flex items-center justify-between pb-3 border-b border-slate-800/60 mb-3">
        <div class="flex items-center space-x-2">
          <div class="w-2 h-2 rounded-full bg-rose-500"></div>
          <h3 class="text-sm font-semibold text-slate-200">资产大类配置</h3>
        </div>
        <div class="text-xs text-slate-400 flex items-center space-x-1.5">
          <span>类别配置比重</span>
        </div>
      </div>

      <div class="flex flex-col sm:flex-row items-center gap-4 flex-1">
        <!-- 环形图 -->
        <div class="w-full sm:w-44 h-44 shrink-0 flex items-center justify-center relative">
          <div ref="typeChartRef" class="w-full h-full"></div>
          <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
            <span class="text-[10px] text-slate-400 font-medium">配置比例</span>
            <span class="text-xs font-bold text-slate-200 mt-0.5">{{ typeList.length }} 大类</span>
          </div>
        </div>

        <!-- 详细结构清单与进度条 -->
        <div class="flex-1 w-full space-y-3">
          <div 
            v-for="item in typeList" 
            :key="item.name"
            class="group p-2 rounded-xl bg-slate-900/60 hover:bg-slate-800/60 border border-slate-800/50 transition-all"
          >
            <div class="flex items-center justify-between text-xs mb-1.5">
              <div class="flex items-center space-x-2">
                <span class="w-2 h-2 rounded-full shrink-0" :style="{ backgroundColor: item.color }"></span>
                <span class="font-medium text-slate-200">{{ item.name }}</span>
              </div>
              <div class="flex items-center space-x-2">
                <span class="font-semibold text-slate-200 num-font">
                  ¥{{ privacyMode ? '••••••' : formatMoney(item.value) }}
                </span>
                <span 
                  class="text-[11px] font-bold num-font px-1.5 py-0.2 rounded"
                  :style="{ color: item.color, backgroundColor: `${item.color}15` }"
                >
                  {{ item.percentage }}%
                </span>
              </div>
            </div>
            <!-- 视觉进度条 -->
            <div class="w-full h-1.5 bg-slate-800/80 rounded-full overflow-hidden">
              <div 
                class="h-full rounded-full transition-all duration-500"
                :style="{ width: `${item.percentage}%`, backgroundColor: item.color }"
              ></div>
            </div>
          </div>

          <div v-if="typeList.length === 0" class="py-6 text-center text-xs text-slate-400">
            暂无资产分类数据
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  platformData: {
    type: Object,
    default: () => ({})
  },
  typeData: {
    type: Object,
    default: () => ({})
  },
  privacyMode: {
    type: Boolean,
    default: false
  }
})

const platformChartRef = ref(null)
const typeChartRef = ref(null)
let platformChart = null
let typeChart = null

const platformConfig = {
  eastmoney: { name: '东方财富 A股', color: '#38bdf8' },
  tiantian: { name: '天天基金', color: '#f59e0b' },
  xueqiu: { name: '雪球基金', color: '#6366f1' },
  yangjibao: { name: '养基宝', color: '#14b8a6' },
  manual: { name: '手动自选', color: '#a855f7' }
}


const typeColorMap = {
  '股票/ETF': '#f43f5e',
  '公募基金': '#38bdf8',
  '场外基金': '#38bdf8',
  '现金': '#10b981',
  '其他': '#94a3b8'
}

const formatMoney = (val) => {
  if (val === undefined || val === null) return '0.00'
  return Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 计算平台资产分布明细
const platformTotal = computed(() => {
  return Object.values(props.platformData).reduce((sum, val) => sum + (Number(val) || 0), 0)
})

const platformList = computed(() => {
  const total = platformTotal.value || 1
  return Object.entries(props.platformData).map(([key, val]) => {
    const num = Number(val) || 0
    const cfg = platformConfig[key] || { name: key, color: '#94a3b8' }
    return {
      key,
      name: cfg.name,
      color: cfg.color,
      value: num,
      percentage: ((num / total) * 100).toFixed(1)
    }
  }).sort((a, b) => b.value - a.value)
})

// 计算类型资产分布明细
const typeTotal = computed(() => {
  return Object.values(props.typeData).reduce((sum, val) => sum + (Number(val) || 0), 0)
})

const typeList = computed(() => {
  const total = typeTotal.value || 1
  return Object.entries(props.typeData).map(([name, val], index) => {
    const num = Number(val) || 0
    const fallbackColors = ['#f43f5e', '#38bdf8', '#10b981', '#f59e0b']
    const color = typeColorMap[name] || fallbackColors[index % fallbackColors.length]
    return {
      name,
      color,
      value: num,
      percentage: ((num / total) * 100).toFixed(1)
    }
  }).sort((a, b) => b.value - a.value)
})

const initCharts = () => {
  if (platformChartRef.value) {
    platformChart = echarts.init(platformChartRef.value)
  }
  if (typeChartRef.value) {
    typeChart = echarts.init(typeChartRef.value)
  }
  renderCharts()
}

const renderCharts = () => {
  if (platformChart) {
    const pData = platformList.value.map(item => ({
      name: item.name,
      value: Math.round(item.value),
      itemStyle: { color: item.color }
    }))
    platformChart.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: '{b}: ¥{c} ({d}%)',
        backgroundColor: '#0f172a',
        borderColor: '#1e293b',
        borderWidth: 1,
        padding: [8, 12],
        textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'ui-monospace, monospace' }
      },
      series: [
        {
          type: 'pie',
          radius: ['62%', '84%'],
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 5,
            borderColor: '#0e1626',
            borderWidth: 2
          },
          label: { show: false },
          labelLine: { show: false },
          emphasis: {
            scale: true,
            scaleSize: 4
          },
          data: pData.length ? pData : [{ name: '暂无持仓', value: 0, itemStyle: { color: '#334155' } }]
        }
      ]
    })
  }

  if (typeChart) {
    const tData = typeList.value.map(item => ({
      name: item.name,
      value: Math.round(item.value),
      itemStyle: { color: item.color }
    }))
    typeChart.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: '{b}: ¥{c} ({d}%)',
        backgroundColor: '#0f172a',
        borderColor: '#1e293b',
        borderWidth: 1,
        padding: [8, 12],
        textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'ui-monospace, monospace' }
      },
      series: [
        {
          type: 'pie',
          radius: ['62%', '84%'],
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 5,
            borderColor: '#0e1626',
            borderWidth: 2
          },
          label: { show: false },
          labelLine: { show: false },
          emphasis: {
            scale: true,
            scaleSize: 4
          },
          data: tData.length ? tData : [{ name: '暂无持仓', value: 0, itemStyle: { color: '#334155' } }]
        }
      ]
    })
  }
}

const handleResize = () => {
  platformChart?.resize()
  typeChart?.resize()
}

watch(() => [props.platformData, props.typeData], () => {
  renderCharts()
}, { deep: true })

onMounted(() => {
  initCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  platformChart?.dispose()
  typeChart?.dispose()
})
</script>

