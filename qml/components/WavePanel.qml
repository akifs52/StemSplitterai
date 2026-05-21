import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property var waveformData: []
    property color waveColor: "#00e388"
    property real playPosition: 0.0
    property bool hasAudio: false
    property string panelLabel: "Original Waveform"

    width: parent ? parent.width : 600
    height: 200
    radius: 16
    color: Qt.rgba(1, 1, 1, 0.03)
    border.color: Qt.rgba(1, 1, 1, 0.06)
    border.width: 1
    clip: true

    function drawEmptyWaveform(ctx, w, h) {
        ctx.strokeStyle = Qt.rgba(1, 1, 1, 0.12)
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.moveTo(0, h * 0.5)
        ctx.lineTo(w, h * 0.5)
        ctx.stroke()
    }

    Column {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 12

        RowLayout {
            width: parent.width
            spacing: 8

            Text { text: "\uE40B"; font.family: "Material Symbols Outlined"; color: "#e2e2e2"; font.pixelSize: 18; Layout.alignment: Qt.AlignVCenter }
            Text {
                text: root.panelLabel
                color: "#e2e2e2"
                font.family: "Inter"
                font.pixelSize: 18
                font.weight: Font.DemiBold
                Layout.alignment: Qt.AlignVCenter
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "Stereo \u2022 48kHz \u2022 24-bit"
                color: Qt.rgba(0.73, 0.8, 0.73, 0.4)
                font.family: "Inter"
                font.pixelSize: 11
                font.letterSpacing: 1.2
                Layout.alignment: Qt.AlignVCenter
            }
        }

        Item {
            width: parent.width
            height: parent.height - 60

            Canvas {
                id: canvas
                anchors.fill: parent

                onPaint: {
                    var ctx = getContext("2d")
                    var w = width
                    var h = height
                    ctx.clearRect(0, 0, w, h)

                    var data = root.waveformData
                    var len = data && data.length !== undefined ? data.length : 0

                    if (!root.hasAudio || len <= 0) {
                        root.drawEmptyWaveform(ctx, w, h)
                        return
                    }

                    var gap = len > w / 2 ? 0 : 1
                    var barW = Math.max(1, w / len - gap)
                    var centerY = h / 2
                    var playedColor = root.waveColor
                    var unplayedColor = Qt.rgba(0.29, 0.29, 0.29, 0.4)

                    for (var j = 0; j < len; j++) {
                        var amp = Math.min(Math.abs(data[j] || 0), 1.0)
                        if (isNaN(amp)) amp = 0
                        var barH = amp * (h * 0.45)
                        ctx.fillStyle = (j / len <= root.playPosition) ? playedColor : unplayedColor
                        ctx.fillRect(j * (barW + gap), centerY - barH / 2, barW, Math.max(barH, 1))
                    }

                    if (root.playPosition > 0) {
                        var px = root.playPosition * w
                        ctx.strokeStyle = root.waveColor
                        ctx.lineWidth = 2
                        ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, h); ctx.stroke()
                        ctx.strokeStyle = Qt.rgba(0, 0.89, 0.53, 0.15)
                        ctx.lineWidth = 6
                        ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, h); ctx.stroke()
                    }
                }

                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                Component.onCompleted: requestPaint()

                Connections {
                    target: root
                    function onWaveformDataChanged() { canvas.requestPaint() }
                    function onPlayPositionChanged() { canvas.requestPaint() }
                    function onHasAudioChanged() { canvas.requestPaint() }
                }
            }
        }
    }
}
