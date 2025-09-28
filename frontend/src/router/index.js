import { createRouter, createWebHistory } from 'vue-router'
import Chat from '../pages/Chat.vue'
import Login from '../pages/Login.vue'
import Register from '../pages/Register.vue'
import RoleLibrary from '../pages/RoleLibrary.vue'
import Membership from '../pages/Membership.vue'
import Profile from '../pages/Profile.vue'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/chat', component: Chat },
  { path: '/role', component: RoleLibrary },
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: '/membership', component: Membership },
  { path: '/profile', component: Profile },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router