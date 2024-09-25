<template>
  <a class="btn btn-default" v-on:click="link">Mark triaged</a>
</template>

<script>
import { errorParser, hideBucketUntil } from "../../helpers";
import HideBucketBtnForm from "./HideBucketBtnForm.vue";
import Vue from "vue";
import swal from "sweetalert";

export default {
  props: {
    bucket: {
      type: Number,
      default: null,
    },
  },
  methods: {
    link() {
      const FormCtor = Vue.extend(HideBucketBtnForm);
      const hideForm = new FormCtor({
        parent: this,
      }).$mount();
      swal({
        title: "Mark bucket triaged",
        content: hideForm.$el,
        buttons: true,
      }).then((value) => {
        if (value) {
          hideBucketUntil(
            this.bucket,
            new Date(
              Date.now() + hideForm.selectedTime * 7 * 24 * 60 * 60 * 1000,
            ),
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
