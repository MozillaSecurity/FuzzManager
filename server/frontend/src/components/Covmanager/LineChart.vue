<script>
import Chart from "chart.js/auto";
import { defineComponent, h, onMounted, onUnmounted, ref } from "vue";

export default defineComponent({
  name: "LineChart",
  props: {
    chartId: {
      type: String,
      default: "line-chart",
    },
    chartdata: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    let chartInstance = null;
    const chartData = ref({
      labels: [],
      datasets: [],
    });

    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          position: "left",
          id: "y-axis-0",
          ticks: {
            suggestedMin: 0,
            suggestedMax: 100,
            beginAtZero: true,
          },
          grid: { display: true },
        },
        y1: {
          position: "right",
          id: "y-axis-1",
          ticks: { beginAtZero: true },
          grid: { display: false },
        },
        x: {
          grid: {
            display: false,
          },
        },
      },
      plugins: {
        tooltip: {
          callbacks: {
            beforeLabel: function (context) {
              return props.chartdata.datasets[context.datasetIndex].created[
                context.dataIndex
              ];
            },
            afterLabel: function (context) {
              if (context.dataIndex > 0) {
                let dataset = props.chartdata.datasets[context.datasetIndex];
                return `\u0394 to last: ${dataset.deltas[context.dataIndex - 1]} ${dataset.unit}`;
              }
            },
          },
        },
      },
    };

    onMounted(() => {
      if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
      }

      const canvas = document.getElementById(props.chartId);
      if (!canvas) return;

      chartData.value.labels = props.chartdata.labels;
      chartData.value.datasets = props.chartdata.datasets;

      chartInstance = new Chart(canvas, {
        type: "line",
        data: chartData.value,
        options: chartOptions,
      });
    });

    onUnmounted(() => {
      if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
      }
    });

    return () =>
      h(
        "div",
        {
          style: {
            width: "100%",
            height: "50vh",
            position: "relative",
          },
        },
        [
          h("canvas", {
            id: props.chartId,
          }),
        ],
      );
  },
});
</script>
