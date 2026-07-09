import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

Item {
    id: actionsRingConfig
    readonly property var theme: Theme.palette(uiState.darkMode)
    property var s: lm.strings

    Component {
        id: ringActionComboDelegate
        ItemDelegate {
            width: parent ? parent.width : implicitWidth
            highlighted: ListView.isCurrentItem
            font { family: uiState.fontFamily; pixelSize: 11 }
            contentItem: Text {
                leftPadding: 10; rightPadding: 10
                text: (lm.strings, lm.trAction(modelData ? modelData.label : ""))
                font { family: uiState.fontFamily; pixelSize: 11 }
                color: highlighted ? actionsRingConfig.theme.accent
                                   : actionsRingConfig.theme.textPrimary
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: highlighted ? Qt.rgba(0, 0.83, 0.67, 0.1) : "transparent"
            }
        }
    }

    function actionIndexForId(actionId) {
        var actions = backend.allActions
        for (var i = 0; i < actions.length; i++)
            if (actions[i].id === actionId) return i
        return 0
    }

    function rebuildSlots(slotIndex, newActionId) {
        var current = backend.actionsRingSlots
        var slots = []
        for (var i = 0; i < current.length; i++)
            slots.push(current[i])
        while (slots.length < 4)
            slots.push("none")
        slots[slotIndex] = newActionId
        backend.setActionsRingSlots(slots)
    }

    ScrollView {
        id: pageScroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        Column {
            id: mainCol
            width: pageScroll.availableWidth
            spacing: 0

            // ── Header ──────────────────────────────────────────────
            Item {
                width: parent.width
                height: 96

                Column {
                    anchors {
                        left: parent.left
                        leftMargin: 36
                        verticalCenter: parent.verticalCenter
                    }
                    spacing: 4

                    Text {
                        text: s["ring.title"] || "Actions Ring"
                        font {
                            family: uiState.fontFamily
                            pixelSize: 24
                            bold: true
                        }
                        color: actionsRingConfig.theme.textPrimary
                    }

                    Text {
                        text: s["ring.subtitle"]
                              || "Configure hold delay and sector actions for the radial menu"
                        font {
                            family: uiState.fontFamily
                            pixelSize: 13
                        }
                        color: actionsRingConfig.theme.textSecondary
                    }
                }
            }

            Rectangle {
                width: parent.width - 72
                height: 1
                color: actionsRingConfig.theme.border
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Item { width: 1; height: 20 }

            // ── Hold Delay Slider Card ───────────────────────────────
            Rectangle {
                width: parent.width - 72
                anchors.horizontalCenter: parent.horizontalCenter
                height: holdDelayContent.implicitHeight + 40
                radius: Theme.radius
                color: actionsRingConfig.theme.bgCard
                border.width: 1
                border.color: actionsRingConfig.theme.border

                Column {
                    id: holdDelayContent
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: 20
                    }
                    spacing: 12

                    Row {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: s["ring.hold_delay"] || "Hold Delay"
                            font {
                                family: uiState.fontFamily
                                pixelSize: 16
                                bold: true
                            }
                            color: actionsRingConfig.theme.textPrimary
                        }

                        Text {
                            text: (holdDelaySlider.pressed
                                   ? Math.round(holdDelaySlider.value)
                                   : backend.actionsRingHoldMs) + " ms"
                            font {
                                family: uiState.fontFamily
                                pixelSize: 14
                            }
                            color: actionsRingConfig.theme.textSecondary
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Text {
                        text: s["ring.hold_delay_desc"]
                              || "How long to hold the thumb button before the ring appears"
                        font {
                            family: uiState.fontFamily
                            pixelSize: 12
                        }
                        color: actionsRingConfig.theme.textSecondary
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    RowLayout {
                        width: parent.width
                        spacing: 12

                        Text {
                            text: "100"
                            font { family: uiState.fontFamily; pixelSize: 11 }
                            color: actionsRingConfig.theme.textDim
                        }

                        WheelSafeSlider {
                            id: holdDelaySlider
                            Layout.fillWidth: true
                            from: 100
                            to: 500
                            stepSize: 10
                            value: backend.actionsRingHoldMs
                            accentColor: actionsRingConfig.theme.accent
                            accentDimColor: actionsRingConfig.theme.accentDim
                            trackColor: actionsRingConfig.theme.border
                            onMoved: holdDelaySave.restart()
                            onPressedChanged: {
                                if (!pressed) {
                                    holdDelaySave.stop()
                                    backend.setActionsRingHoldMs(Math.round(value))
                                }
                            }
                        }

                        Text {
                            text: "500"
                            font { family: uiState.fontFamily; pixelSize: 11 }
                            color: actionsRingConfig.theme.textDim
                        }

                        Rectangle {
                            Layout.preferredWidth: 80
                            Layout.preferredHeight: 36
                            radius: 10
                            color: actionsRingConfig.theme.accentDim

                            Text {
                                id: holdDelayLabel
                                anchors.centerIn: parent
                                text: (holdDelaySlider.pressed
                                       ? Math.round(holdDelaySlider.value)
                                       : backend.actionsRingHoldMs) + " ms"
                                font {
                                    family: uiState.fontFamily
                                    pixelSize: 14
                                    bold: true
                                }
                                color: actionsRingConfig.theme.accent
                            }
                        }
                    }

                    Timer {
                        id: holdDelaySave
                        interval: 250
                        repeat: false
                        onTriggered: backend.setActionsRingHoldMs(
                            Math.round(holdDelaySlider.value))
                    }
                }
            }

            Item { width: 1; height: 16 }

            // ── Ring Slot Editor Card ────────────────────────────────
            Rectangle {
                width: parent.width - 72
                anchors.horizontalCenter: parent.horizontalCenter
                height: slotsContent.implicitHeight + 40
                radius: Theme.radius
                color: actionsRingConfig.theme.bgCard
                border.width: 1
                border.color: actionsRingConfig.theme.border

                Column {
                    id: slotsContent
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: 20
                    }
                    spacing: 12

                    Text {
                        text: s["ring.slots_title"] || "Ring Actions"
                        font {
                            family: uiState.fontFamily
                            pixelSize: 16
                            bold: true
                        }
                        color: actionsRingConfig.theme.textPrimary
                    }

                    Text {
                        text: s["ring.slots_desc"]
                              || "Choose the actions available in each sector of the radial menu"
                        font {
                            family: uiState.fontFamily
                            pixelSize: 12
                        }
                        color: actionsRingConfig.theme.textSecondary
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    Repeater {
                        model: 4

                        delegate: RowLayout {
                            width: slotsContent.width
                            spacing: 12

                            Text {
                                text: (s["ring.slot_prefix"] || "Slot ") + (index + 1)
                                Layout.preferredWidth: 60
                                font {
                                    family: uiState.fontFamily
                                    pixelSize: 12
                                    bold: true
                                }
                                color: actionsRingConfig.theme.textPrimary
                            }

                            ComboBox {
                                Layout.fillWidth: true
                                model: backend.allActions
                                textRole: "label"
                                delegate: ringActionComboDelegate
                                Material.accent: actionsRingConfig.theme.accent
                                font { family: uiState.fontFamily; pixelSize: 11 }
                                currentIndex: {
                                    var slots = backend.actionsRingSlots
                                    var aid = (slots && index < slots.length)
                                              ? slots[index] : "none"
                                    return actionsRingConfig.actionIndexForId(aid)
                                }
                                displayText: {
                                    var slots = backend.actionsRingSlots
                                    var aid = (slots && index < slots.length)
                                              ? slots[index] : "none"
                                    return (lm.strings,
                                            lm.trAction(backend.actionLabelFor(aid)))
                                }
                                onActivated: function(idx) {
                                    var aid = backend.allActions[idx].id
                                    actionsRingConfig.rebuildSlots(index, aid)
                                }
                            }
                        }
                    }
                }
            }

            Item { width: 1; height: 32 }
        }
    }
}
