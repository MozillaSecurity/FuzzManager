import Vue from "vue"
import CreateOrEdit from "./components/Signatures/CreateOrEdit.vue"

export default new Vue({
    el: '#app',
    components: {
        'createoredit': CreateOrEdit,
    }
})
