<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-4">
    <!-- 1. 总资产净值 (主资产锚点) -->
    <div class="fin-glow-card bg-[#0e1626]/90 border border-slate-800/80 hover:border-slate-700/90 rounded-2xl p-5 relative overflow-hidden shadow-sm flex flex-col justify-between">
      <div>
        <div class="flex items-center justify-between text-slate-400 mb-2.5">
          <span class="text-xs font-semibold tracking-wider text-slate-300">总资产净值</span>
          <div class="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Wallet class="w-3.5 h-3.5" />
          </div>
        </div>

        <div class="text-2xl sm:text-3xl lg:text-[32px] font-extrabold text-white tracking-tight num-font flex items-baseline">
          <span class="text-lg text-slate-400 mr-1 font-semibold">¥</span>
          <template v-if="privacyMode">
            <span class="tracking-widest text-slate-400">••••••</span>
          </template>
          <template v-else>
            <span>{{ splitNumber(summary.total_asset)[0] }}</span>
            <span class="text-lg sm:text-xl text-slate-400 font-semibold">.{{ splitNumber(summary.total_asset)[1] }}</span>
          </template>
        </div>
      </div>

      <div class="mt-3.5 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
        <div class="text-slate-400 flex items-center space-x-1.5">
          <span>持仓总成本:</span>
          <span class="font-medium text-slate-300 num-font">
            ¥{{ privacyMode ? '••••••' : formatNumber(summary.total_cost) }}
          </span>
        </div>
        <span 
          class="num-font text-[11px] font-semibold px-1.5 py-0.5 rounded"
          :class="summary.total_profit >= 0 ? 'text-rose-400 bg-rose-500/10' : 'text-emerald-400 bg-emerald-500/10'"
        >
          {{ summary.total_profit >= 0 ? '+' : '' }}{{ summary.total_profit_rate }}%
        </span>
      </div>
    </div>

    <!-- 2. 今日实时盈亏 -->
    <div class="fin-glow-card bg-[#0e1626]/90 border border-slate-800/80 hover:border-slate-700/90 rounded-2xl p-5 relative overflow-hidden shadow-sm flex flex-col justify-between">
      <div>
        <div class="flex items-center justify-between text-slate-400 mb-2.5">
          <div class="flex items-center space-x-1.5">
            <span class="text-xs font-semibold tracking-wider text-slate-300">今日预计盈亏</span>
            <span class="text-[10px] px-1 py-0.2 rounded bg-slate-800 text-slate-400 font-medium">实时</span>
          </div>
          <div 
            class="p-1.5 rounded-lg border"
            :class="summary.today_profit >= 0 
              ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' 
              : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'"
          >
            <component :is="summary.today_profit >= 0 ? TrendingUp : TrendingDown" class="w-3.5 h-3.5" />
          </div>
        </div>

        <div 
          class="text-2xl sm:text-3xl lg:text-[32px] font-extrabold tracking-tight num-font flex items-baseline"
          :class="summary.today_profit >= 0 ? 'text-rose-400' : 'text-emerald-400'"
        >
          <template v-if="privacyMode">
            <span class="tracking-widest text-slate-400">••••••</span>
          </template>
          <template v-else>
            <span class="text-lg mr-0.5 font-semibold">{{ summary.today_profit >= 0 ? '+' : '-' }}¥</span>
            <span>{{ splitNumber(Math.abs(summary.today_profit))[0] }}</span>
            <span class="text-lg sm:text-xl opacity-80 font-semibold">.{{ splitNumber(Math.abs(summary.today_profit))[1] }}</span>
          </template>
        </div>
      </div>

      <div class="mt-3.5 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
        <div class="flex items-center space-x-1.5">
          <span 
            class="px-2 py-0.5 rounded-full text-xs font-bold num-font border"
            :class="summary.today_profit >= 0 
              ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' 
              : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'"
          >
            {{ summary.today_profit >= 0 ? '+' : '' }}{{ summary.today_profit_rate }}%
          </span>
          <span class="text-slate-400 text-[11px]">日收益率</span>
        </div>
        <span class="text-[11px] text-slate-400">基于实时估值</span>
      </div>
    </div>

    <!-- 3. 累计总浮动盈亏 -->
    <div class="fin-glow-card bg-[#0e1626]/90 border border-slate-800/80 hover:border-slate-700/90 rounded-2xl p-5 relative overflow-hidden shadow-sm flex flex-col justify-between">
      <div>
        <div class="flex items-center justify-between text-slate-400 mb-2.5">
          <span class="text-xs font-semibold tracking-wider text-slate-300">累计总盈亏</span>
          <div class="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <BarChart3 class="w-3.5 h-3.5" />
          </div>
        </div>

        <div 
          class="text-2xl sm:text-3xl lg:text-[32px] font-extrabold tracking-tight num-font flex items-baseline"
          :class="summary.total_profit >= 0 ? 'text-rose-400' : 'text-emerald-400'"
        >
          <template v-if="privacyMode">
            <span class="tracking-widest text-slate-400">••••••</span>
          </template>
          <template v-else>
            <span class="text-lg mr-0.5 font-semibold">{{ summary.total_profit >= 0 ? '+' : '-' }}¥</span>
            <span>{{ splitNumber(Math.abs(summary.total_profit))[0] }}</span>
            <span class="text-lg sm:text-xl opacity-80 font-semibold">.{{ splitNumber(Math.abs(summary.total_profit))[1] }}</span>
          </template>
        </div>
      </div>

      <div class="mt-3.5 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
        <div class="flex items-center space-x-1.5">
          <span 
            class="px-2 py-0.5 rounded-full text-xs font-bold num-font border"
            :class="summary.total_profit >= 0 
              ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' 
              : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'"
          >
            {{ summary.total_profit >= 0 ? '+' : '' }}{{ summary.total_profit_rate }}%
          </span>
          <span class="text-slate-400 text-[11px]">历史总回报</span>
        </div>
        <span class="text-[11px] text-slate-400">跨账户汇总</span>
      </div>
    </div>

    <!-- 4. 在管标的与监听状态 -->
    <div class="fin-glow-card bg-[#0e1626]/90 border border-slate-800/80 hover:border-slate-700/90 rounded-2xl p-5 relative overflow-hidden shadow-sm flex flex-col justify-between">
      <div>
        <div class="flex items-center justify-between text-slate-400 mb-2.5">
          <span class="text-xs font-semibold tracking-wider text-slate-300">在管持仓标的</span>
          <div class="p-1.5 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Layers class="w-3.5 h-3.5" />
          </div>
        </div>

        <div class="text-2xl sm:text-3xl lg:text-[32px] font-extrabold text-white tracking-tight num-font flex items-baseline">
          <span>{{ summary.position_count || 0 }}</span>
          <span class="text-xs sm:text-sm font-normal text-slate-400 ml-2">只标的在管</span>
        </div>
      </div>

      <div class="mt-3.5 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
        <div class="flex items-center space-x-1.5 text-slate-400 text-xs">
          <span class="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span class="text-slate-300 font-medium">秒级行情轮询中</span>
        </div>
        <span class="text-[11px] text-slate-400">交易时段静默更新</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Wallet, TrendingUp, TrendingDown, BarChart3, Layers } from 'lucide-vue-next'

defineProps({
  summary: {
    type: Object,
    default: () => ({
      total_asset: 0,
      total_cost: 0,
      today_profit: 0,
      today_profit_rate: 0,
      total_profit: 0,
      total_profit_rate: 0,
      position_count: 0
    })
  },
  privacyMode: {
    type: Boolean,
    default: false
  }
})

// 分离整数和小数部分
const splitNumber = (val) => {
  if (val === undefined || val === null) return ['0', '00']
  const formatted = Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const parts = formatted.split('.')
  return [parts[0], parts[1] || '00']
}

const formatNumber = (val) => {
  if (val === undefined || val === null) return '0.00'
  return Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

