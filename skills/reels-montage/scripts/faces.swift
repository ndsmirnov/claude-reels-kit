// Лица на картинке/кадре через Apple Vision (02.10.2026: субтитры не должны заходить на лица героев).
// faces <image> → JSON [[x0,y0,x1,y1], …] в долях кадра, y сверху вниз. Собирать: swiftc -O faces.swift -o faces
import Foundation
import Vision
import AppKit

let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("[]"); exit(0) }
var boxes: [[Double]] = []
let face = VNDetectFaceRectanglesRequest()
let human = VNDetectHumanRectanglesRequest()   // запасной: стилизованные 3D-лица детектор лиц иногда пропускает
human.upperBodyOnly = true
try? VNImageRequestHandler(cgImage: cg).perform([face, human])
for o in (face.results ?? []) {
    let b = o.boundingBox
    boxes.append([b.minX, 1 - b.maxY, b.maxX, 1 - b.minY])
}
if boxes.isEmpty {
    for o in (human.results ?? []) {   // голова ≈ верхняя треть рамки верхней части тела
        let b = o.boundingBox
        boxes.append([b.minX, 1 - b.maxY, b.maxX, 1 - b.maxY + b.height / 3])
    }
}
let data = try! JSONSerialization.data(withJSONObject: boxes)
print(String(data: data, encoding: .utf8)!)
