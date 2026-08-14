// icon_tool.swift — flatten + resize brand icon (no external deps)
// usage: swift icon_tool.swift <src.png> <bgHexRRGGBB|none> <size> <out.png> [scale]
// scale: logo occupies scale*size centered (default 1.0 = full bleed)
import AppKit
import CoreGraphics

let args = CommandLine.arguments
guard args.count >= 5 else {
    FileHandle.standardError.write("usage: icon_tool <src> <bgHex|none> <size> <out> [scale]\n".data(using: .utf8)!)
    exit(2)
}
let srcPath = args[1], bgHex = args[2]
let size = Int(args[3])!, outPath = args[4]
let scale = args.count > 5 ? Double(args[5])! : 1.0

guard let src = NSImage(contentsOfFile: srcPath),
      let srcCG = src.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("cannot read \(srcPath)\n".data(using: .utf8)!)
    exit(1)
}

let cs = CGColorSpace(name: CGColorSpace.sRGB)!
let ctx = CGContext(
    data: nil, width: size, height: size, bitsPerComponent: 8, bytesPerRow: 0,
    space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
)!

if bgHex != "none" {
    let v = UInt32(bgHex, radix: 16)!
    let r = CGFloat((v >> 16) & 0xFF) / 255, g = CGFloat((v >> 8) & 0xFF) / 255, b = CGFloat(v & 0xFF) / 255
    ctx.setFillColor(CGColor(colorSpace: cs, components: [r, g, b, 1])!)
    ctx.fill(CGRect(x: 0, y: 0, width: size, height: size))
}

let inset = Double(size) * (1.0 - scale) / 2.0
ctx.interpolationQuality = .high
ctx.draw(srcCG, in: CGRect(x: inset, y: inset, width: Double(size) - inset * 2, height: Double(size) - inset * 2))

let outCG = ctx.makeImage()!
let rep = NSBitmapImageRep(cgImage: outCG)
// strip alpha when background is opaque (App Store 1024 requires no alpha)
let pngData: Data
if bgHex != "none" {
    let opaqueCtx = CGContext(
        data: nil, width: size, height: size, bitsPerComponent: 8, bytesPerRow: 0,
        space: cs, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue
    )!
    opaqueCtx.draw(outCG, in: CGRect(x: 0, y: 0, width: size, height: size))
    pngData = NSBitmapImageRep(cgImage: opaqueCtx.makeImage()!).representation(using: .png, properties: [:])!
} else {
    pngData = rep.representation(using: .png, properties: [:])!
}
do {
    try pngData.write(to: URL(fileURLWithPath: outPath))
} catch {
    FileHandle.standardError.write("write failed: \(error)\n".data(using: .utf8)!)
    exit(1)
}
