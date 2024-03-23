/*
 * @license: BSD
 *
 * All rights reserved. This program and the accompanying materials are made
 * available under the terms of the BSD which accompanies this distribution, and
 * is available at U{http://www.opensource.org/licenses/bsd-license.php}
 */

// JavaScript script to retrieve mouse cursor/pointer position via KWin API

let mouse_pos = {
    "mouse-pointer-pos.x": workspace.cursorPos.x,
    "mouse-pointer-pos.y": workspace.cursorPos.y
};

const json_output = JSON.stringify(mouse_pos);
console.info(json_output)
