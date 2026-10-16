<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
    <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-150">
      <!-- 头部 -->
      <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h3 class="font-bold text-slate-100 flex items-center space-x-2">
            <Send class="w-4 h-4 text-emerald-400" />
            <span>微信通知设置</span>
          </h3>
          <p class="text-xs text-slate-400 mt-0.5">微信接收开盘提醒、收盘日报和涨跌提醒</p>
        </div>
        <button @click="$emit('close')" class="text-slate-400 hover:text-white transition">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- 内容主体 -->
      <div class="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
        <!-- 主配置卡片 -->
        <div class="p-4 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-4">
          <!-- 启用开关 -->
          <div class="flex items-center justify-between pb-3 border-b border-slate-800/80">
            <div>
              <div class="font-bold text-sm text-slate-200">开启微信通知</div>
              <div class="text-[11px] text-slate-400">开启后将通过微信向你推送提醒</div>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="config.enabled" class="sr-only peer" />
              <div class="w-10 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
            </label>
          </div>

          <!-- Token 输入 -->
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label class="block text-xs font-medium text-slate-300">微信通知 Token (PushPlus)</label>
              <a 
                href="http://www.pushplus.plus" 
                target="_blank" 
                rel="noreferrer"
                class="text-xs text-emerald-400 hover:text-emerald-300 transition flex items-center gap-1"
              >
                <span>获取 Token</span>
                <ExternalLink class="w-3 h-3" />
              </a>
            </div>
            <input 
              v-model="config.token" 
              type="text" 
              placeholder="请粘贴 Token (如: abc12345...)" 
              class="w-full bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-xl px-3.5 py-2.5 font-mono focus:outline-none focus:border-emerald-500 transition"
            />
            <p class="text-[11px] text-slate-500 mt-1">进入 PushPlus 官网微信扫码登录，在「一对一推送」复制 Token</p>
          </div>

          <!-- 推送事件开关 -->
          <div class="pt-3 border-t border-slate-800/80 space-y-2">
            <div class="text-xs font-medium text-slate-400 mb-2">提醒时机</div>
            <div class="grid grid-cols-2 gap-2 text-xs text-slate-300">
              <label class="flex items-center space-x-2 cursor-pointer p-2 rounded-lg bg-slate-900/50 hover:bg-slate-900 transition border border-slate-800">
                <input type="checkbox" v-model="config.notify_on_open" class="rounded bg-slate-800 border-slate-700 text-emerald-500 focus:ring-0" />
                <span>09:25 开盘提醒</span>
              </label>
              <label class="flex items-center space-x-2 cursor-pointer p-2 rounded-lg bg-slate-900/50 hover:bg-slate-900 transition border border-slate-800">
                <input type="checkbox" v-model="config.notify_on_close" class="rounded bg-slate-800 border-slate-700 text-emerald-500 focus:ring-0" />
                <span>15:05 收盘日报</span>
              </label>
              <label class="flex items-center space-x-2 cursor-pointer p-2 rounded-lg bg-slate-900/50 hover:bg-slate-900 transition border border-slate-800">
                <input type="checkbox" v-model="config.notify_on_alert" class="rounded bg-slate-800 border-slate-700 text-emerald-500 focus:ring-0" />
                <span>大幅涨跌提醒</span>
              </label>
              <label class="flex items-center space-x-2 cursor-pointer p-2 rounded-lg bg-slate-900/50 hover:bg-slate-900 transition border border-slate-800">
                <input type="checkbox" v-model="config.notify_on_night_fund" class="rounded bg-slate-800 border-slate-700 text-emerald-500 focus:ring-0" />
                <span>21:45 基金净值更新</span>
              </label>
            </div>
          </div>

          <!-- 保存按钮 -->
          <div class="pt-2 flex justify-end">
            <button 
              @click="saveConfig" 
              :disabled="saving"
              class="px-4 py-2 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl shadow transition disabled:opacity-50"
            >
              {{ saving ? '保存中...' : '保存设置' }}
            </button>
          </div>
        </div>

        <!-- 测试推送栏 -->
        <div class="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-between">
          <div>
            <div class="text-xs font-bold text-emerald-400">测试微信通知</div>
            <div class="text-[11px] text-slate-400">发一条测试消息到微信，确认是否能正常收到</div>
          </div>
          <button 
            @click="sendTestMsg"
            :disabled="testing || !config.token"
            class="px-4 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl shadow transition disabled:opacity-50 shrink-0"
          >
            {{ testing ? '发送中...' : '发送测试' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Send, X, ExternalLink } from 'lucide-vue-next'
import { getNotifications, updateNotification, testNotification } from '../api'

defineProps({
  visible: Boolean
})

const config = ref({
  channel: 'pushplus',
  name: '微信PushPlus推送',
  token: '',
  enabled: false,
  notify_on_open: true,
  notify_on_close: true,
  notify_on_alert: true,
  notify_on_night_fund: true
})

const saving = ref(false)
const testing = ref(false)

const fetchConfig = async () => {
  try {
    const res = await getNotifications()
    const items = res.data || []
    const pp = items.find(i => i.channel === 'pushplus')
    if (pp) {
      config.value = { ...config.value, ...pp }
    }
  } catch (e) {
    console.error('获取通知配置失败:', e)
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    await updateNotification('pushplus', config.value)
    alert('微信通知设置已保存！')
  } catch (e) {
    alert('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

const sendTestMsg = async () => {
  if (!config.value.token) {
    alert('请先填写 Token 并保存！')
    return
  }
  testing.value = true
  try {
    await testNotification('pushplus')
    alert('测试消息已发送，请在微信中查看！')
  } catch (e) {
    alert('测试发送失败: ' + e.message)
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>
