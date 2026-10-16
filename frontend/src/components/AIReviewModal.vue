<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/70 backdrop-blur-md">
    <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
      
      <!-- 头部栏 -->
      <div class="px-5 py-3.5 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between shrink-0">
        <div class="flex items-center space-x-2.5">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white">
            <Sparkles class="w-4 h-4" />
          </div>
          <div>
            <h3 class="font-bold text-slate-100 text-sm">AI 持仓分析与调仓建议</h3>
            <p class="text-[11px] text-slate-400">结合实盘成本与盈亏，针对性分析风险与操作点位</p>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <button 
            @click="showConfig = !showConfig" 
            class="text-[11px] px-2.5 py-1 rounded-lg border transition flex items-center space-x-1.5"
            :class="hasKey ? 'bg-slate-800 text-slate-300 border-slate-700' : 'bg-amber-500/10 text-amber-400 border-amber-500/30'"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="hasKey ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'"></span>
            <span>{{ hasKey ? '接口正常' : '配置 Key' }}</span>
          </button>
          <button @click="$emit('close')" class="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800">
            <X class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- 内容主体 -->
      <div class="flex-1 overflow-y-auto p-5 space-y-4">
        
        <!-- API 配置折叠区 -->
        <div v-if="showConfig" class="p-3 bg-slate-950 rounded-xl border border-indigo-500/30 space-y-2 text-xs">
          <div class="flex justify-between text-indigo-300">
            <span>大模型接口 (OpenAI 协议兼容)</span>
            <span v-if="maskedKey" class="text-emerald-400 text-[10px]">生效中: {{ maskedKey }}</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <input v-model="config.api_key" type="password" :placeholder="maskedKey || 'sk-...'" class="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono" />
            <input v-model="config.api_base" type="text" placeholder="https://api.deepseek.com/v1" class="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono" />
            <input v-model="config.model" type="text" placeholder="deepseek-chat" class="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono" />
          </div>
          <div class="flex justify-end space-x-2 pt-1">
            <button @click="showConfig = false" class="px-2.5 py-1 bg-slate-800 text-slate-300 rounded-lg">取消</button>
            <button @click="saveConfig" class="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg">保存</button>
          </div>
        </div>

        <!-- 持仓数据与快速勾选（直接平铺，消除用户疑虑） -->
        <div class="bg-slate-950/70 rounded-xl border border-slate-800 p-3.5 space-y-2.5">
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center space-x-2">
              <span class="font-medium text-slate-200">本次带入持仓 (已选 {{ selectedCodes.length }}/{{ allPositions.length }} 只)</span>
              <span class="text-slate-400">总市值 ¥{{ formatNum(selectedMarketValue) }}</span>
            </div>
            <!-- 快捷范围按钮 -->
            <div class="flex space-x-1">
              <button 
                v-for="f in scopeFilters" :key="f.key"
                @click="applyScope(f.key)"
                class="px-2 py-0.5 rounded text-[11px] border transition"
                :class="currentScope === f.key ? 'bg-indigo-600/30 text-indigo-300 border-indigo-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'"
              >
                {{ f.label }}
              </button>
            </div>
          </div>

          <!-- 持仓选择列表卡片 -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-1.5 max-h-44 overflow-y-auto pr-1">
            <div 
              v-for="p in allPositions" :key="p.code"
              @click="togglePos(p.code)"
              class="p-2 rounded-lg border text-xs cursor-pointer select-none flex items-center justify-between transition"
              :class="selectedCodes.includes(p.code) ? 'bg-indigo-950/30 border-indigo-500/40 text-slate-100' : 'bg-slate-900/40 border-slate-800/80 text-slate-500 opacity-60'"
            >
              <div class="flex items-center space-x-1.5 truncate">
                <div class="w-3.5 h-3.5 rounded border flex items-center justify-center shrink-0"
                  :class="selectedCodes.includes(p.code) ? 'bg-indigo-600 border-indigo-500 text-white' : 'border-slate-700 bg-slate-800'">
                  <Check v-if="selectedCodes.includes(p.code)" class="w-2.5 h-2.5" />
                </div>
                <div class="truncate">
                  <div class="font-medium truncate">{{ p.name }}</div>
                  <div class="text-[10px] text-slate-400">成本 ¥{{ Number(p.cost_price).toFixed(2) }} ➔ 现价 ¥{{ Number(p.current_price).toFixed(2) }}</div>
                </div>
              </div>
              <div class="text-right shrink-0 pl-2">
                <div class="font-semibold text-[11px]" :class="(p.total_profit_rate || 0) >= 0 ? 'text-rose-400' : 'text-emerald-400'">
                  {{ (p.total_profit_rate || 0) >= 0 ? '+' : '' }}{{ Number(p.total_profit_rate || 0).toFixed(2) }}%
                </div>
                <div class="text-[10px] text-slate-500">占 {{ getWeight(p.market_value) }}%</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 分析选项区 -->
        <div class="bg-slate-950/70 rounded-xl border border-slate-800 p-3.5 space-y-3">
          <!-- 关注重点（多选 Pills） -->
          <div>
            <div class="text-xs text-slate-300 font-medium mb-1.5">关注重点 (多选)</div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
              <button 
                v-for="opt in focusOptions" :key="opt.id"
                @click="toggleFocus(opt.id)"
                class="px-2.5 py-1.5 rounded-lg border text-xs font-medium text-left flex items-center justify-between transition"
                :class="selectedFocus.includes(opt.id) ? 'bg-purple-950/40 border-purple-500/50 text-purple-200' : 'bg-slate-900 border-slate-800 text-slate-400'"
              >
                <span>{{ opt.name }}</span>
                <Check v-if="selectedFocus.includes(opt.id)" class="w-3 h-3 text-purple-400 shrink-0" />
              </button>
            </div>
          </div>

          <!-- 投资风格 & 分析深度 -->
          <div class="grid grid-cols-2 gap-3 text-xs pt-1 border-t border-slate-800/80">
            <div>
              <div class="text-slate-400 mb-1">投资偏好</div>
              <div class="grid grid-cols-3 gap-1">
                <button 
                  v-for="s in styleOptions" :key="s.id"
                  @click="style = s.id"
                  class="py-1 rounded border text-center text-[11px] transition"
                  :class="style === s.id ? 'bg-indigo-600/30 border-indigo-500/50 text-indigo-300 font-semibold' : 'bg-slate-900 border-slate-800 text-slate-400'"
                >
                  {{ s.name }}
                </button>
              </div>
            </div>
            <div>
              <div class="text-slate-400 mb-1">报告形式</div>
              <div class="grid grid-cols-2 gap-1">
                <button 
                  v-for="d in depthOptions" :key="d.id"
                  @click="depth = d.id"
                  class="py-1 rounded border text-center text-[11px] transition"
                  :class="depth === d.id ? 'bg-indigo-600/30 border-indigo-500/50 text-indigo-300 font-semibold' : 'bg-slate-900 border-slate-800 text-slate-400'"
                >
                  {{ d.name }}
                </button>
              </div>
            </div>
          </div>

          <!-- 补充提问 & 生成按钮 -->
          <div class="pt-1">
            <div class="flex space-x-2">
              <input 
                v-model="customPrompt" 
                type="text" 
                placeholder="补充具体疑问（如：套牢的怎么加仓拉平成本...）" 
                class="flex-1 bg-slate-900 border border-slate-700 text-slate-100 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500"
                @keyup.enter="handleReview"
              />
              <button 
                @click="handleReview" 
                :disabled="loading || selectedCodes.length === 0"
                class="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold rounded-lg transition disabled:opacity-40 flex items-center space-x-1.5 shrink-0"
              >
                <Sparkles v-if="!loading" class="w-3.5 h-3.5" />
                <Loader2 v-else class="w-3.5 h-3.5 animate-spin" />
                <span>{{ loading ? '分析中...' : '开始分析' }}</span>
              </button>
            </div>
            <div class="flex flex-wrap gap-1.5 mt-2">
              <button 
                v-for="chip in quickChips" :key="chip"
                @click="customPrompt = chip"
                class="px-2 py-0.5 bg-slate-900 text-slate-400 hover:text-slate-200 rounded text-[11px] border border-slate-800"
              >
                {{ chip }}
              </button>
            </div>
          </div>
        </div>

        <!-- 报告结果区 -->
        <div v-if="analysisResult" class="bg-slate-950 rounded-xl border border-purple-500/40 p-4 space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-800 text-xs">
            <span class="font-semibold text-purple-300 flex items-center space-x-1.5">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span>分析与调仓建议</span>
            </span>
            <div class="flex space-x-2">
              <button @click="copyResult" class="px-2 py-0.5 bg-slate-800 text-slate-300 hover:text-white rounded flex items-center space-x-1">
                <Copy class="w-3 h-3" />
                <span>{{ copied ? '已复制' : '复制' }}</span>
              </button>
              <button @click="handleReview" :disabled="loading" class="px-2 py-0.5 bg-slate-800 text-indigo-400 rounded flex items-center space-x-1">
                <RefreshCw class="w-3 h-3" :class="loading ? 'animate-spin' : ''" />
                <span>重试</span>
              </button>
            </div>
          </div>
          <div class="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap select-text">
            {{ analysisResult }}
          </div>
        </div>

      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { X, Sparkles, Loader2, Check, Copy, RefreshCw } from 'lucide-vue-next'
import axios from 'axios'

const props = defineProps({
  visible: Boolean,
  positions: { type: Array, default: () => [] },
  summary: { type: Object, default: () => ({}) }
})

defineEmits(['close'])

const showConfig = ref(false)
const hasKey = ref(false)
const maskedKey = ref('')
const config = ref({ api_key: '', api_base: 'https://api.deepseek.com/v1', model: 'deepseek-chat' })

const currentScope = ref('all')
const selectedCodes = ref([])
const selectedFocus = ref(['loss_recovery', 'trade_points'])
const style = ref('balanced')
const depth = ref('detailed')
const customPrompt = ref('')
const loading = ref(false)
const analysisResult = ref('')
const copied = ref(false)

const focusOptions = [
  { id: 'loss_recovery', name: '📉 亏损解套诊断' },
  { id: 'position_risk', name: '⚖️ 仓位集中排查' },
  { id: 'valuation', name: '💰 估值加仓时机' },
  { id: 'trade_points', name: '🎯 具体买卖点位' }
]

const styleOptions = [
  { id: 'conservative', name: '稳健保本' },
  { id: 'balanced', name: '均衡配置' },
  { id: 'aggressive', name: '积极进取' }
]

const depthOptions = [
  { id: 'detailed', name: '逐只深度诊断' },
  { id: 'concise', name: '精炼清单' }
]

const quickChips = [
  '重点分析亏损最多的持仓怎么处理',
  '哪些持仓占比过高需要减仓防守？',
  '结合估值看哪些适合逢低分批加仓？',
  '请帮我制定具体的止盈止损计划'
]

const scopeFilters = [
  { key: 'all', label: '全部', fn: () => true },
  { key: 'loss', label: '仅亏损', fn: p => (p.total_profit_rate || 0) < 0 || (p.today_profit_rate || 0) < 0 },
  { key: 'etf', label: '仅基金/ETF', fn: p => p.is_etf || /^(51|15|16)/.test(p.code) || p.name.includes('ETF') },
  { key: 'top5', label: '前5大', fn: null }
]

const allPositions = computed(() => props.positions || [])

const selectedMarketValue = computed(() => {
  return allPositions.value
    .filter(p => selectedCodes.value.includes(p.code))
    .reduce((sum, p) => sum + (Number(p.market_value) || 0), 0)
})

const getWeight = (mv) => {
  const total = Number(props.summary?.total_asset) || selectedMarketValue.value || 1
  return ((Number(mv || 0) / total) * 100).toFixed(1)
}

const formatNum = (val) => Number(val || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const applyScope = (key) => {
  currentScope.value = key
  if (key === 'top5') {
    selectedCodes.value = [...allPositions.value].sort((a, b) => (Number(b.market_value) || 0) - (Number(a.market_value) || 0)).slice(0, 5).map(p => p.code)
  } else {
    const f = scopeFilters.find(item => item.key === key)
    selectedCodes.value = allPositions.value.filter(f ? f.fn : () => true).map(p => p.code)
  }
}

const togglePos = (code) => {
  const i = selectedCodes.value.indexOf(code)
  if (i > -1) selectedCodes.value.splice(i, 1)
  else selectedCodes.value.push(code)
  currentScope.value = 'custom'
}

const toggleFocus = (id) => {
  const i = selectedFocus.value.indexOf(id)
  if (i > -1 && selectedFocus.value.length > 1) selectedFocus.value.splice(i, 1)
  else if (i === -1) selectedFocus.value.push(id)
}

const fetchConfig = async () => {
  try {
    const res = await axios.get('/api/ai/config')
    hasKey.value = res.data.has_key
    maskedKey.value = res.data.masked_key || ''
    if (res.data.api_base) config.value.api_base = res.data.api_base
    if (res.data.model) config.value.model = res.data.model
  } catch (e) {}
}

const saveConfig = async () => {
  try {
    await axios.post('/api/ai/config', config.value)
    hasKey.value = true
    showConfig.value = false
    await fetchConfig()
  } catch (e) {
    alert('保存失败: ' + e.message)
  }
}

const handleReview = async () => {
  if (selectedCodes.value.length === 0) return alert('请至少勾选一只持仓')
  loading.value = true
  analysisResult.value = ''
  try {
    const res = await axios.post('/api/ai/review', {
      prompt: customPrompt.value,
      codes: selectedCodes.value,
      focus_areas: selectedFocus.value,
      investment_style: style.value,
      detail_level: depth.value
    })
    analysisResult.value = res.data.analysis
  } catch (e) {
    analysisResult.value = '分析失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

const copyResult = () => {
  navigator.clipboard.writeText(analysisResult.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

watch(() => props.positions, (pos) => {
  if (pos?.length && selectedCodes.value.length === 0) selectedCodes.value = pos.map(p => p.code)
}, { immediate: true })

onMounted(() => {
  fetchConfig()
  if (allPositions.value.length) selectedCodes.value = allPositions.value.map(p => p.code)
})
</script>
