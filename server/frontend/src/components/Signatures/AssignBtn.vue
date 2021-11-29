<template>
  <a class="btn btn-default" v-on:click="link">Assign an existing bug</a>
</template>

<script>
import { assignExternalBug, errorParser } from "../../helpers";
import AssignBtnForm from "./AssignBtnForm.vue";
import Vue from "vue";
import swal from "sweetalert";

export default {
  props: {
    bucket: {
      type: Number,
      default: null,
    },
    providers: {
      type: Array,
      default: null,
    },
  },
  methods: {
    link() {
      const FormCtor = Vue.extend(AssignBtnForm);
      const linkForm = new FormCtor({
        parent: this,
        propsData: {
          providers: this.providers,
        },
      }).$mount();
      swal({
        title: "Assign existing bug",
        content: linkForm.$el,
        buttons: true,
      }).then((value) => {
        if (value) {
          assignExternalBug(
            this.bucket,
            linkForm.externalBugId,
            linkForm.selectedProvider
          )
            .then((data) => {
              window.location.href = data.url;
            })
            .catch((err) => {
              swal("Oops", errorParser(err), "error");
            });
        }
      });
    },
  },
};
</script>
