import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

export const darkChartOptions = (yLabel) => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 300 },
  interaction: { mode: "index", intersect: false },
  plugins: {
    legend: {
      labels: { color: "#7c8a99", font: { family: "IBM Plex Mono", size: 10 } },
    },
    tooltip: {
      backgroundColor: "#1a222c",
      borderColor: "#38495c",
      borderWidth: 1,
      titleFont: { family: "IBM Plex Mono", size: 11 },
      bodyFont: { family: "IBM Plex Mono", size: 11 },
    },
  },
  scales: {
    x: {
      ticks: { color: "#4d5967", font: { family: "IBM Plex Mono", size: 9 }, maxTicksLimit: 8 },
      grid: { color: "#1e2833" },
    },
    y: {
      title: { display: !!yLabel, text: yLabel, color: "#7c8a99", font: { family: "IBM Plex Mono", size: 10 } },
      ticks: { color: "#4d5967", font: { family: "IBM Plex Mono", size: 9 } },
      grid: { color: "#1e2833" },
    },
  },
});
