<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
    <div class="bg-slate-900/95 border border-slate-800 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl shadow-black/80 flex flex-col max-h-[88vh]">
      
      <!-- 顶栏 -->
      <div class="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between shrink-0">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <BellRing class="w-4 h-4" />
          </div>
          <div>
            <h3 class="font-bold text-slate-100 text-sm sm:text-base tracking-tight flex items-center gap-2">
              <span>涨跌提醒与止盈止损</span>
              <span class="text-[11px] font-normal text-slate-400">股票 & ETF</span>
            </h3>
            <p class="text-xs text-slate-400">达到设定的涨跌幅或收益目标时，自动发送微信通知</p>
          </div>
        </div>
        <button 
          @click="$emit('close')" 
          class="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition active:scale-95"
          title="关闭"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- 主体滚动区 -->
      <div class="p-5 sm:p-6 space-y-5 overflow-y-auto flex-1 text-slate-200">
        
        <!-- 添加提醒区域 (极简内联表单，无繁重套娃框) -->
        <div class="space-y-3">
          <!-- 快捷预设 Pills -->
          <div class="flex items-center justify-between text-xs">
            <span class="text-slate-400 font-medium">常用预设快捷填入</span>
            <span v-if="errorMsg" class="text-rose-400 text-[11px] font-medium">{{ errorMsg }}</span>
          </div>

          <div class="flex flex-wrap gap-2">
            <button 
              type="button"
              v-for="preset in presets" 
              :key="preset.title"
              @click="applyPreset(preset)"
              class="px-3 py-1.5 rounded-lg border text-xs transition active:scale-95 flex items-center space-x-1.5 cursor-pointer"
              :class="activePresetTitle === preset.title 
                ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300 font-medium shadow-sm' 
                : 'bg-slate-800/60 border-slate-700/60 hover:border-slate-600 text-slate-300'"
            >
              <span>{{ preset.title }}</span>
              <span class="text-[10px] font-mono px-1 rounded" :class="getRuleBadge(preset.rule_type)">{{ preset.valText }}</span>
            </button>
          </div>

          <!-- 表单控件组 -->
          <form @submit.prevent="handleAddRule" class="grid grid-cols-1 sm:grid-cols-12 gap-2 pt-1">
            <!-- 1. 标的选择 -->
            <div class="sm:col-span-5">
              <select 
                v-model="newRule.code" 
                @change="onSelectPosition" 
                class="w-full bg-slate-800/90 border border-slate-700/80 text-slate-100 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:border-emerald-500 transition cursor-pointer"
                required
              >
                <option value="" disabled>选择股票或基金...</option>
                <option v-for="p in positions" :key="p.id" :value="p.code">
                  {{ isEtfCode(p.code, p.name) ? '[基金] ' : '[股票] ' }}{{ p.name }} ({{ p.code }})
                </option>
              </select>
            </div>

            <!-- 2. 规则类型 -->
            <div class="sm:col-span-4">
              <select 
                v-model="newRule.rule_type" 
                class="w-full bg-slate-800/90 border border-slate-700/80 text-slate-100 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:border-emerald-500 transition cursor-pointer"
              >
                <option value="stop_profit">累计盈利达到 (止盈)</option>
                <option value="day_change_below">今日下跌超过</option>
                <option value="day_change_above">今日上涨超过</option>
                <option value="stop_loss">累计亏损达到 (止损)</option>
              </select>
            </div>

            <!-- 3. 阈值与添加按钮 -->
            <div class="sm:col-span-3 flex space-x-2">
              <div class="relative flex-1">
                <input 
                  v-model.number="newRule.threshold" 
                  type="number" 
                  step="0.1" 
                  min="0.1"
                  placeholder="目标比例" 
                  class="w-full bg-slate-800/90 border border-slate-700/80 text-slate-100 text-xs rounded-xl pl-3 pr-6 py-2.5 font-mono focus:outline-none focus:border-emerald-500 transition"
                  required
                />
                <span class="absolute right-2.5 top-2.5 text-xs text-slate-400 pointer-events-none">%</span>
              </div>
              <button 
                type="submit" 
                :disabled="submitting"
                class="px-4 py-2.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white rounded-xl transition shrink-0 disabled:opacity-50 cursor-pointer"
              >
                {{ submitting ? '添加中' : '添加' }}
              </button>
            </div>
          </form>
        </div>

        <!-- 现存规则列表 -->
        <div class="space-y-2 pt-2">
          <div class="flex items-center justify-between border-t border-slate-800/80 pt-4">
            <div class="text-xs font-semibold text-slate-300 flex items-center space-x-1.5">
              <span>已添加的提醒</span>
              <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 text-slate-400 border border-slate-700 font-mono">
                {{ rules.length }}
              </span>
            </div>
            <span class="text-[11px] text-slate-500">交易时间内自动检测</span>
          </div>

          <!-- 规则卡片容器 -->
          <div class="space-y-1.5">
            <div 
              v-for="rule in rules" 
              :key="rule.id" 
              class="px-3.5 py-2.5 bg-slate-800/40 hover:bg-slate-800/70 rounded-xl border border-slate-800/70 hover:border-slate-700 flex items-center justify-between text-xs transition duration-150 group"
            >
              <div class="flex items-center space-x-3">
                <span 
                  class="px-1.5 py-0.5 rounded text-[10px] font-medium"
                  :class="isEtfCode(rule.code, rule.name) ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20' : 'bg-slate-700/40 text-slate-300 border border-slate-600/30'"
                >
                  {{ isEtfCode(rule.code, rule.name) ? '基金' : '股票' }}
                </span>
                
                <div class="flex items-center space-x-2">
                  <span class="font-medium text-slate-200 text-xs sm:text-sm">{{ rule.name }}</span>
                  <span class="text-slate-500 font-mono text-[11px]">{{ rule.code }}</span>
                </div>
              </div>

              <div class="flex items-center space-x-2.5">
                <!-- 规则状态 Badge (高对比度清爽配色) -->
                <div class="px-2.5 py-0.8 rounded-md text-xs font-medium font-mono" :class="getRuleBadge(rule.rule_type)">
                  {{ formatRuleText(rule) }}
                </div>

                <!-- 删除按钮 -->
                <button 
                  @click="deleteRule(rule.id)" 
                  class="text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 p-1.5 rounded-lg transition active:scale-95"
                  title="删除此提醒"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>

            <!-- 空列表占位 -->
            <div v-if="rules.length === 0" class="py-8 text-center rounded-xl border border-dashed border-slate-800 bg-slate-900/20">
              <div class="w-9 h-9 rounded-full bg-slate-800/60 flex items-center justify-center mx-auto text-slate-500 mb-2">
                <BellOff class="w-4 h-4" />
              </div>
              <p class="text-xs font-medium text-slate-400">暂无提醒规则</p>
              <p class="text-[11px] text-slate-500 mt-1">选择上方股票或基金，点击预设即可快速添加</p>
            </div>
          </div>
        </div>

      </div>

      <!-- 弹窗底栏 (遵循 GEMINI.md 通俗规范：移除“标的”等黑话) -->
      <div class="px-6 py-3.5 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs text-slate-400 shrink-0">
        <div class="flex items-center space-x-2">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span>达到目标自动微信通知，同一股票或基金 1 小时内不重复提醒</span>
        </div>
        <button 
          @click="$emit('close')" 
          class="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition active:scale-95 text-xs font-medium cursor-pointer"
        >
          完成
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { BellRing, BellOff, X, Trash2 } from 'lucide-vue-next'
import { getAlertRules, createAlertRule, deleteAlertRule } from '../api'

const props = defineProps({
  visible: Boolean,
  positions: {
    type: Array,
    default: () => []
  }
})

const rules = ref([])
const activePresetTitle = ref('')
const submitting = ref(false)
const errorMsg = ref('')

const newRule = ref({
  code: '',
  name: '',
  rule_type: 'stop_profit',
  threshold: 15.0,
  enabled: true
})

// 常用预设推荐列表 (精简 Pill 形式)
const presets = [
  { title: '稳健止盈', valText: '+15%', rule_type: 'stop_profit', threshold: 15.0 },
  { title: '高抛止盈', valText: '+25%', rule_type: 'stop_profit', threshold: 25.0 },
  { title: '低吸补仓', valText: '-2%', rule_type: 'day_change_below', threshold: 2.0 },
  { title: '严格止损', valText: '-8%', rule_type: 'stop_loss', threshold: 8.0 }
]

// 判断是否为基金
const isEtfCode = (code, name = '') => /^(51|15|16|58)/.test(String(code || '').trim()) || /ETF|指数|LOF|联接/.test(name || '')

const fetchRules = async () => {
  try {
    const res = await getAlertRules()
    rules.value = res.data || []
  } catch (e) {
    console.error(e)
  }
}

const onSelectPosition = () => {
  errorMsg.value = ''
  const p = props.positions.find(item => item.code === newRule.value.code)
  if (p) {
    newRule.value.name = p.name
    if (isEtfCode(p.code, p.name) && newRule.value.rule_type === 'stop_loss') {
      newRule.value.rule_type = 'stop_profit'
      newRule.value.threshold = 15.0
    }
  }
}

// 应用预设
const applyPreset = (preset) => {
  activePresetTitle.value = preset.title
  newRule.value.rule_type = preset.rule_type
  newRule.value.threshold = preset.threshold
}

const handleAddRule = async () => {
  errorMsg.value = ''
  if (!newRule.value.code) {
    errorMsg.value = '请先选择股票或基金'
    return
  }
  if (!newRule.value.name) onSelectPosition()
  
  submitting.value = true
  try {
    await createAlertRule(newRule.value)
    newRule.value.code = ''
    newRule.value.name = ''
    activePresetTitle.value = ''
    await fetchRules()
  } catch (e) {
    errorMsg.value = '添加失败: ' + (e.message || '网络错误')
  } finally {
    submitting.value = false
  }
}

const deleteRule = async (id) => {
  try {
    await deleteAlertRule(id)
    await fetchRules()
  } catch (e) {
    console.error(e)
  }
}

const formatRuleText = (r) => {
  const map = {
    day_change_above: `今日涨超 +${r.threshold}%`,
    day_change_below: `今日跌超 -${r.threshold}%`,
    stop_profit: `止盈 +${r.threshold}%`,
    stop_loss: `止损 -${r.threshold}%`
  }
  return map[r.rule_type] || `${r.threshold}%`
}

const badgeMap = {
  day_change_below: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
  stop_loss: 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
}
const getRuleBadge = (type) => badgeMap[type] || 'bg-rose-500/15 text-rose-300 border border-rose-500/30'

onMounted(() => {
  fetchRules()
})
</script>
