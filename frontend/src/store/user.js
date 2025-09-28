import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: ()=>({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  getters:{
    isLogin: (s)=> !!s.token
  },
  actions:{
    setAuth(token, user){
      this.token = token
      this.user = user
      localStorage.setItem('token', token || '')
      localStorage.setItem('user', user ? JSON.stringify(user) : 'null')
    },
    logout(){
      this.setAuth('', null)
    }
  }
})